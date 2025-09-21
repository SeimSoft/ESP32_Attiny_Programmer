#include <avr/io.h>
#include <util/delay.h>

int main(void)
{
  DDRB |= _BV(PB4); // PB4 ist jetzt Ausgang


 while (1) {

    PORTB &= ~_BV(PB4); // PB4=Low -> LED an
    _delay_ms(10); // Warte 250ms

    PORTB |= _BV(PB4); // PB4=High -> LED aus
    _delay_ms(10); // Warte 250ms
  }

  return 0;
}
