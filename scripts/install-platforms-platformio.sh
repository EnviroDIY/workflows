#!/bin/bash

# Set options,
set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

echo "::group::Installing Platforms and Frameworks"
echo "\e[32mInstalling Atmel AVR platforms \e[0m"
pio pkg install -g --platform atmelavr
pio pkg install -g --tool framework-arduino-avr
pio pkg install -g --tool tool-avrdude
pio pkg install -g --tool toolchain-atmelavr

echo "\e[32mInstalling Atmel AVR framework \e[0m"
pio pkg install -g --platform atmelmegaavr
pio pkg install -g --tool framework-arduino-megaavr

echo "\e[32mInstalling Atmel SAM platform \e[0m"
pio pkg install -g --platform atmelsam

echo "\e[32mInstalling Atmel SAM framework \e[0m"
pio pkg install -g --tool framework-arduino-samd
pio pkg install -g --tool framework-arduino-samd-adafruit
pio pkg install -g --tool framework-arduino-samd-sodaq
pio pkg install -g --tool framework-cmsis
pio pkg install -g --tool framework-cmsis-atmel
pio pkg install -g --tool tool-bossac
pio pkg install -g --tool toolchain-gccarmnoneeabi
echo "::endgroup::"

echo "\n\e[32mInstalling the ESP8266 Arduino Core\e[0m"
pio pkg install -g --platform espressif8266

echo "\n\e[32mInstalling the ESP32 Arduino Core\e[0m"
pio pkg install -g --platform espressif32

echo "\n\e[32mInstalling the Raspberry Pi Pico Arduino Core\e[0m"
pio pkg install -g --platform raspberrypi

echo "\n\e[32mInstalling the STM32 Arduino Core\e[0m"
pio pkg install -g --platform ststm32

echo "\n\e[32mInstalling the Teensy Core\e[0m"
pio pkg install -g --platform teensy

echo "::group::Current globally installed packages"
echo "\e[32m\nCurrently installed packages:\e[0m"
pio pkg list -g -v
echo "::endgroup::"
