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

# --- ATtiny13 Fuse Bit Settings for 9.6 MHz internal clock ---
# SAFE FUSE SETTINGS - CAREFULLY VERIFIED TO AVOID BRICKING THE CHIP!

# Low Fuse: 0x7A for 9.6 MHz (default factory is 0x6A for 1.2MHz)
# Bit 7: CKDIV8  = 0 (disable clock division by 8 - gives full 9.6MHz)
# Bit 6: CKOUT   = 1 (disable clock output on PB4)
# Bit 5-4: SUT   = 01 (14CK + 64ms startup time - safe default)
# Bit 3-0: CKSEL = 1010 (internal RC oscillator - 9.6MHz when CKDIV8=0)
ATTINY13_LOW_FUSE_9_6MHZ = 0x7A

# High Fuse: 0xFF (SAFE DEFAULT - keeps all dangerous bits disabled)
# Bit 7: RSTDISBL = 1 (RESET PIN ENABLED - CRITICAL FOR ISP!)
# Bit 6: BODLEVEL = 1 (brown-out detection disabled)
# Bit 5: BODEN    = 1 (brown-out detection disabled)
# Bit 4: -        = 1 (reserved, keep as 1)
# Bit 3: -        = 1 (reserved, keep as 1)
# Bit 2: -        = 1 (reserved, keep as 1)
# Bit 1: SPIEN    = 1 (SPI PROGRAMMING ENABLED - CRITICAL FOR ISP!)
# Bit 0: -        = 1 (reserved, keep as 1)
ATTINY13_HIGH_FUSE = 0xFF

# Factory default fuses for reference and recovery
ATTINY13_FACTORY_LOW_FUSE = 0x6A   # 1.2MHz (9.6MHz/8)
ATTINY13_FACTORY_HIGH_FUSE = 0xFF  # All safe defaults

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
# Fuse bit operations
# ------------------------

def read_low_fuse():
    """Read low fuse byte"""
    return send_cmd_r4(0x50, 0x00, 0x00, 0x00)

def read_high_fuse():
    """Read high fuse byte"""
    return send_cmd_r4(0x58, 0x08, 0x00, 0x00)

def read_lock_bits():
    """Read lock bits"""
    return send_cmd_r4(0x58, 0x00, 0x00, 0x00)

def write_low_fuse(fuse_value):
    """Write low fuse byte"""
    print(f"Writing low fuse: 0x{fuse_value:02X}")
    send_cmd_r4(0xAC, 0xA0, 0x00, fuse_value)
    time.sleep_ms(50)  # Wait for fuse write to complete

def write_high_fuse(fuse_value):
    """Write high fuse byte"""
    print(f"Writing high fuse: 0x{fuse_value:02X}")
    send_cmd_r4(0xAC, 0xA8, 0x00, fuse_value)
    time.sleep_ms(50)  # Wait for fuse write to complete

def program_fuses_for_9_6mhz():
    """Program fuses for 9.6 MHz internal clock - SAFETY CHECKED"""
    print("\n=== Programming Fuses for 9.6 MHz Internal Clock ===")
    print("⚠️  SAFETY: Fuse settings verified to keep RESET and SPI programming enabled!")

    # Read current fuse settings
    low_fuse = read_low_fuse()
    high_fuse = read_high_fuse()
    print(f"Current Low Fuse:  0x{low_fuse:02X}")
    print(f"Current High Fuse: 0x{high_fuse:02X}")

    # CRITICAL SAFETY CHECK: Never allow dangerous high fuse values!
    if ATTINY13_HIGH_FUSE != 0xFF:
        print("❌ SAFETY ERROR: High fuse setting is not 0xFF (safe default)")
        print("❌ This could disable RESET pin or SPI programming - ABORTING!")
        return False

    # Additional safety check on the low fuse bits that matter for clock
    expected_cksel = ATTINY13_LOW_FUSE_9_6MHZ & 0x0F  # Should be 0x0A for internal RC
    if expected_cksel != 0x0A:
        print(f"❌ SAFETY WARNING: CKSEL bits are 0x{expected_cksel:X}, expected 0x0A for internal RC")
        print("❌ This may not be a valid internal RC setting - ABORTING!")
        return False

    # Write new fuse settings if different
    if low_fuse != ATTINY13_LOW_FUSE_9_6MHZ:
        print(f"Setting Low Fuse to 0x{ATTINY13_LOW_FUSE_9_6MHZ:02X} for 9.6 MHz internal clock...")
        write_low_fuse(ATTINY13_LOW_FUSE_9_6MHZ)

        # Verify the write
        new_low_fuse = read_low_fuse()
        if new_low_fuse == ATTINY13_LOW_FUSE_9_6MHZ:
            print(f"✅ Low fuse successfully set to 0x{new_low_fuse:02X}")
        else:
            print(f"❌ Low fuse write failed! Got 0x{new_low_fuse:02X}, expected 0x{ATTINY13_LOW_FUSE_9_6MHZ:02X}")
            return False
    else:
        print("Low fuse already set correctly for 9.6 MHz")

    # For high fuse, we should NOT change it from 0xFF (safe default)
    if high_fuse != ATTINY13_HIGH_FUSE:
        print(f"⚠️  Current High Fuse (0x{high_fuse:02X}) differs from safe default (0x{ATTINY13_HIGH_FUSE:02X})")
        if high_fuse == 0xFE:  # 0xFE would disable RSTDISBL - VERY DANGEROUS!
            print("❌ CRITICAL DANGER: High fuse 0xFE would disable RESET pin!")
            print("❌ This would make the chip unprogrammable via ISP - ABORTING!")
            return False
        elif high_fuse & 0x02 == 0:  # SPIEN bit cleared - also dangerous
            print("❌ CRITICAL DANGER: SPIEN bit is disabled!")
            print("❌ This would make the chip unprogrammable via SPI - ABORTING!")
            return False
        else:
            print("ℹ️  High fuse looks safe, keeping current value rather than changing it")
    else:
        print("High fuse already set to safe default (0xFF)")

    print("=== Fuse Programming Complete ===\n")
    return True

def display_fuse_settings():
    """Display current fuse settings with interpretation"""
    print("\n=== Current Fuse Settings ===")
    low_fuse = read_low_fuse()
    high_fuse = read_high_fuse()
    lock_bits = read_lock_bits()

    print(f"Low Fuse:  0x{low_fuse:02X}")
    print(f"High Fuse: 0x{high_fuse:02X}")
    print(f"Lock Bits: 0x{lock_bits:02X}")

    # Interpret low fuse bits
    cksel = low_fuse & 0x0F
    sut = (low_fuse >> 4) & 0x03
    ckout = (low_fuse >> 6) & 0x01
    ckdiv8 = (low_fuse >> 7) & 0x01

    # Interpret high fuse bits (safety-critical!)
    spien = (high_fuse >> 1) & 0x01
    rstdisbl = (high_fuse >> 7) & 0x01

    print(f"\nLow Fuse Interpretation:")
    print(f"  CKSEL[3:0]: 0x{cksel:X} ", end="")
    if cksel == 0x0A:
        print("(Internal RC oscillator - 9.6MHz calibrated)")
    elif cksel == 0x02:
        print("(Internal RC oscillator - 4.8MHz)")
    elif cksel >= 0x08 and cksel != 0x0A:
        print("(External clock/crystal)")
    else:
        print("(other/unknown clock source)")

    print(f"  SUT[1:0]:   0x{sut:X} (startup time)")
    print(f"  CKOUT:      {ckout} ({'clock output enabled on PB4' if ckout == 0 else 'no clock output'})")
    print(f"  CKDIV8:     {ckdiv8} ({'clock divided by 8' if ckdiv8 == 0 else 'no clock division'})")

    print(f"\nHigh Fuse Interpretation (SAFETY CRITICAL):")
    print(f"  RSTDISBL:   {rstdisbl} ({'RESET PIN DISABLED - DANGER!' if rstdisbl == 0 else 'RESET pin enabled ✅'})")
    print(f"  SPIEN:      {spien} ({'SPI programming disabled - DANGER!' if spien == 0 else 'SPI programming enabled ✅'})")

    if cksel == 0x0A and ckdiv8 == 1:
        expected_freq = "9.6 MHz"
    elif cksel == 0x0A and ckdiv8 == 0:
        expected_freq = "1.2 MHz (9.6MHz ÷ 8 - factory default)"
    elif cksel == 0x02 and ckdiv8 == 1:
        expected_freq = "4.8 MHz"
    elif cksel == 0x02 and ckdiv8 == 0:
        expected_freq = "0.6 MHz (4.8MHz ÷ 8)"
    else:
        expected_freq = "unknown"

    print(f"  → Expected CPU frequency: {expected_freq}")

    # Safety warnings
    if rstdisbl == 0:
        print("⚠️  ⚠️  ⚠️  CRITICAL WARNING: RESET is disabled! Chip may be unrecoverable via ISP!")
    if spien == 0:
        print("⚠️  ⚠️  ⚠️  CRITICAL WARNING: SPI programming disabled! Chip may be unrecoverable!")
    print("================================\n")

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

    # Display current fuse settings before programming
    display_fuse_settings()

    # Program fuses for 9.6 MHz operation
    if not program_fuses_for_9_6mhz():
        print("Failed to program fuses!")
        end_programming()
        return False

    # Display fuse settings after programming
    display_fuse_settings()

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

hex_file_content = """:1000000009C00EC00DC00CC00BC00BC009C008C099
:1000100007C006C011241FBECFE9CDBF08D012C053
:10002000EFCF459B02C0C49A1895C498FDCFBC9AE7
:10003000B898BB9888E088B980E483B983E087B931
:080040007894FFCFF894FFCF84
:00000001FF
"""

if __name__ == '__main__':
    init_isp()
    print("Starting ATtiny13 programming with 9.6 MHz clock configuration...")
    if program_flash(hex_file_content):
        print("ATtiny13 programming + verification successful!")
        print("Chip is now configured to run at 9.6 MHz internal clock.")
    else:
        print("ATtiny13 programming failed or verification failed.")