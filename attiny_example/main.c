#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/delay.h>

int main(void)
{
  DDRB |= _BV(PB4); // PB4 ist jetzt Ausgang
  DDRB &= ~_BV(PB0); // PB0 (AIN0) als Eingang
  DDRB &= ~_BV(PB3); // PB3 (ADC3) als Eingang

  // Analog Comparator Setup:
  // - AIN0 (PB0) als +
  // - ADC3 (PB3) als - (über Multiplexer)
  // - Interrupt bei Output-Änderung
  ACSR = (1 << ACIE); // Interrupt enable, Multiplexer off (AIN1 als -)
  ADCSRB = (1 << ACME); // Multiplexer enable für negativen Eingang
  ADMUX = 0x03; // ADC3 als negativer Eingang

  sei(); // Interrupts global aktivieren

  while (1) {
    // Hauptschleife tut nichts, alles per Interrupt
  }

  return 0;
}

ISR(ANA_COMP_vect) {
  // Setze PB4 je nach Komparator-Ausgang
  if (ACSR & (1 << ACO)) {
    PORTB |= _BV(PB4); // PB4 High
  } else {
    PORTB &= ~_BV(PB4); // PB4 Low
  }
  //_delay_us(1); // Sehr kurze Sperre (Software-Hysterese)
}
