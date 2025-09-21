import machine
import time

# --- Pin Definitions ---
SCK_PIN   = 8
MOSI_PIN  = 10
MISO_PIN  = 9
RESET_PIN = 20

# --- ISP Timing ---
SCK_DELAY_US = 50   # ~100 kHz SCK

# ATtiny13 parameters - CORRECTED VALUES
FLASH_SIZE = 1024  # 1K bytes total
ATTINY13_PAGE_SIZE = 32   # ATtiny13 has 16 words = 32 bytes per page  
ATTINY13_WORDS_PER_PAGE = 16  # 16 words per page
ATTINY13_TOTAL_PAGES = 32     # 32 pages total (32 * 32 = 1024 bytes)

# --- Initialize Pins ---
sck   = machine.Pin(SCK_PIN, machine.Pin.OUT)
mosi  = machine.Pin(MOSI_PIN, machine.Pin.OUT)
miso  = machine.Pin(MISO_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
reset = machine.Pin(RESET_PIN, machine.Pin.OUT)

# ------------------------
# Low-level helpers
# ------------------------

def transfer_byte(byte):
    read_val = 0
    for i in range(8):
        bit = (byte >> (7 - i)) & 0x01
        mosi.value(bit)
        time.sleep_us(SCK_DELAY_US)
        sck.value(1)
        time.sleep_us(SCK_DELAY_US)
        read_val = (read_val << 1) | miso.value()
        sck.value(0)
        time.sleep_us(SCK_DELAY_US)
    return read_val

def send_cmd(a, b, c, d):
    r1 = transfer_byte(a)
    r2 = transfer_byte(b)
    r3 = transfer_byte(c)
    r4 = transfer_byte(d)
    print(f"CMD [{a:02X} {b:02X} {c:02X} {d:02X}] -> RESP [{r1:02X} {r2:02X} {r3:02X} {r4:02X}]")
    return r3, r4

def send_cmd_r3(a, b, c, d):
    return send_cmd(a, b, c, d)[0]

def send_cmd_r4(a, b, c, d):
    return send_cmd(a, b, c, d)[1]

# ------------------------
# ISP interface
# ------------------------

def init_isp():
    sck.value(0)
    mosi.value(0)
    reset.value(1)
    time.sleep_ms(10)

def start_programming():
    reset.value(0)
    time.sleep_ms(20)  # Give chip time to enter reset
    r3 = send_cmd_r3(0xAC, 0x53, 0x00, 0x00)
    if r3 == 0x53:
        print("Programming mode entered successfully.")
        return True
    else:
        print(f"Failed to enter programming mode (got 0x{r3:02X}).")
        return False

def end_programming():
    reset.value(1)
    time.sleep_ms(1)

# ------------------------
# High-level operations
# ------------------------

def chip_erase():
    print("Performing chip erase...")
    send_cmd_r4(0xAC, 0x80, 0x00, 0x00)
    time.sleep_ms(100)  # Wait for erase to complete
    print("Chip erase complete.")

def read_signature_bytes():
    sig = []
    for addr in [0x00, 0x01, 0x02]:
        val = send_cmd_r4(0x30, 0x00, addr, 0x00)
        sig.append(val)
    return sig

def program_flash_page(page_address, data_bytes):
    """Write a page to ATtiny13 flash. ATtiny13 has 16 words (32 bytes) per page."""
    
    # Load page buffer - ATtiny13 has 16 words per page  
    for word_index in range(ATTINY13_WORDS_PER_PAGE):
        byte_index = word_index * 2
        
        # Get low and high bytes
        if byte_index < len(data_bytes):
            low_byte = data_bytes[byte_index]
        else:
            low_byte = 0xFF
            
        if byte_index + 1 < len(data_bytes):
            high_byte = data_bytes[byte_index + 1]
        else:
            high_byte = 0xFF
        
        # Load program memory page (low byte)
        send_cmd_r4(0x40, 0x00, word_index, low_byte)
        # Load program memory page (high byte)  
        send_cmd_r4(0x48, 0x00, word_index, high_byte)

    # Write program memory page
    # The page address should be the word address of the page start
    page_word_addr = page_address // 2
    high_addr = (page_word_addr >> 8) & 0xFF
    low_addr = page_word_addr & 0xFF
    
    print(f"Writing page at word address 0x{page_word_addr:04X} (byte addr 0x{page_address:04X})")
    send_cmd_r4(0x4C, high_addr, low_addr, 0x00)
    time.sleep_ms(50)  # Wait for page write to complete

def parse_hex_file(hex_content):
    data = {}
    for line in hex_content.strip().splitlines():
        if not line.startswith(':'):
            continue
        byte_count = int(line[1:3], 16)
        addr       = int(line[3:7], 16)
        record_type= int(line[7:9], 16)
        if record_type == 0:  # Data record
            for i in range(byte_count):
                data[addr + i] = int(line[9 + i*2: 11 + i*2], 16)
        elif record_type == 1:  # EOF
            break
    return data

def read_flash_byte(addr):
    word_addr = addr >> 1
    high_low  = addr & 0x01
    cmd = 0x28 if high_low else 0x20
    return send_cmd_r4(cmd, (word_addr >> 8) & 0xFF, word_addr & 0xFF, 0x00)

def verify_flash(parsed_data):
    print("Verifying flash contents...")
    errors = 0
    for addr, expected in parsed_data.items():
        actual = read_flash_byte(addr)
        if actual != expected:
            print(f"Mismatch at 0x{addr:04X}: expected 0x{expected:02X}, got 0x{actual:02X}")
            errors += 1
            if errors >= 20:  # Show more errors for debugging
                print(f"... stopping after 20 errors")
                break
    if errors == 0:
        print("Verification PASSED ✅")
        return True
    else:
        print(f"Verification FAILED ❌ with {errors}+ errors")
        return False

def program_flash(hex_content):
    parsed_data = parse_hex_file(hex_content)
    if not parsed_data:
        print("No valid data found in hex file.")
        return False

    print(f"Parsed {len(parsed_data)} bytes from hex file")
    print(f"Address range: 0x{min(parsed_data.keys()):04X} to 0x{max(parsed_data.keys()):04X}")

    if not start_programming():
        return False

    sig = read_signature_bytes()
    print(f"Read signature: {sig} (hex: {[hex(x) for x in sig]})")
    
    # Compare signature - ATtiny13 signature is 0x1E, 0x90, 0x07
    if sig != [30, 144, 7]:  # 0x1E, 0x90, 0x07 in decimal
        print("Error: Detected chip is not an ATtiny13!")
        print(f"Expected: [30, 144, 7] (0x1E, 0x90, 0x07)")
        print(f"Got: {sig} ({[hex(x) for x in sig]})")
        end_programming()
        return False

    chip_erase()

    # Program using correct page size for ATtiny13 (32 bytes per page)
    for page_start in range(0, FLASH_SIZE, ATTINY13_PAGE_SIZE):
        page_data = []
        page_has_data = False
        
        for i in range(ATTINY13_PAGE_SIZE):
            byte_addr = page_start + i
            if byte_addr in parsed_data:
                page_data.append(parsed_data[byte_addr])
                page_has_data = True
            else:
                page_data.append(0xFF)
        
        # Only program pages that have data
        if page_has_data:
            print(f"Programming page {page_start // ATTINY13_PAGE_SIZE} at address 0x{page_start:04X}...")
            program_flash_page(page_start, page_data)

    print("Flash programming complete.")
    ok = verify_flash(parsed_data)
    end_programming()
    return ok

# ------------------------
# Main execution
# ------------------------

hex_file_content = """:1000000009C00EC00DC00CC00BC00AC009C008C09A
:1000100007C006C011241FBECFE9CDBF02D011C05A
:10002000EFCFBC9AC4988FEB9DE50197F1F700C024
:100030000000C49A8FEB9DE50197F1F700C0000026
:06004000F1CFF894FFCFA0
:00000001FF
"""

if __name__ == '__main__':
    init_isp()
    print("Starting ATtiny13 programming...")
    if program_flash(hex_file_content):
        print("ATtiny13 programming + verification successful!")
    else:
        print("ATtiny13 programming failed or verification failed.")
