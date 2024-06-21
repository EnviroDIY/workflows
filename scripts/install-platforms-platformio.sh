#!/bin/bash

# Set options,
set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

echo "\e[32mCurrent PlatformIO version:\e[0m"
pio --version

echo "::group::AVR"
echo "\e[32mInstalling Atmel AVR platforms and Tools \e[0m"
pio pkg install -g --platform atmelavr
pio pkg install -g --tool framework-arduino-avr
pio pkg install -g --tool tool-avrdude
pio pkg install -g --tool toolchain-atmelavr
echo "::endgroup::"

echo "::group::MegaAVR"
echo "\e[32mInstalling Atmel Mega AVR Platform\e\0m"
pio pkg install -g --platform atmelmegaavr
pio pkg install -g --tool framework-arduino-megaavr
pio pkg install -g --tool toolchain-atmelavr
echo "::endgroup::"

echo "::group::Atmel SAM/SAMD"
echo "\e[32mInstalling Atmel SAM/SAMD Platform\e\0m"
pio pkg install -g --platform atmelsam
pio pkg install -g --tool framework-arduino-sam
pio pkg install -g --tool framework-arduino-samd
pio pkg install -g --tool framework-arduino-samd-adafruit
pio pkg install -g --tool framework-arduino-samd-sodaq
pio pkg install -g --tool framework-cmsis
pio pkg install -g --tool framework-cmsis-atmel
pio pkg install -g --tool toolchain-gccarmnoneeabi
echo "::endgroup::"

echo "::group::Espressif ESP8266"
echo "\e[32mInstalling Espressif ESP8266 Platform\e\0m"
echo "\e[32mInstalling the ESP8266 Arduino Platform\e[0m"
pio pkg install -g --platform espressif8266
pio pkg install -g --tool tool-esptool
pio pkg install -g --tool tool-esptoolpy
pio pkg install -g --tool toolchain-xtensa
echo "::endgroup::"

echo "::group::Espressif ESP32"
echo "\e[32mInstalling the ESP32 Arduino Platform\e\0m"
pio pkg install -g --platform espressif32
pio pkg install -g --tool tool-esptool
pio pkg install -g --tool tool-esptoolpy
pio pkg install -g --tool toolchain-riscv32-esp
pio pkg install -g --tool toolchain-xtensa-esp32
echo "::endgroup::"

echo "::group::Raspberry Pi Pico"
echo "\e[32mInstalling the Raspberry Pi Pico Arduino Platform\e\0m"
pio pkg install -g --platform raspberrypi
pio pkg install -g --tool framework-arduino-mbed
pio pkg install -g --tool tool-rp2040tools
pio pkg install -g --tool toolchain-gccarmnoneeabi
echo "::endgroup::"

echo "::group::Renesas"
echo "\e[32mInstalling the Renesas-RA Arduino Platform\e\0m"
pio pkg install -g --platform renesas-ra
pio pkg install -g --tool framework-arduinorenesas-uno
pio pkg install -g --tool tool-bossac
pio pkg install -g --tool toolchain-gccarmnoneeabi
echo "::endgroup::"

echo "::group::NRF52"
echo "\e[32mInstalling the NRF52 Arduino Platform\e\0m"
pio pkg install -g --platform nordicnrf52
pio pkg install -g --tool framework-cmsis
pio pkg install -g --tool tool-adafruit-nrfutil
pio pkg install -g --tool tool-sreccat
pio pkg install -g --tool toolchain-gccarmnoneeabi
echo "::endgroup::"

echo "::group::STM32"
echo "\e[32mInstalling the STM32 Arduino Platform\e\0m"
pio pkg install -g --platform ststm32
pio pkg install -g --tool framework-arduino-mbed
pio pkg install -g --tool framework-arduinoststm32
pio pkg install -g --tool framework-cmsis
pio pkg install -g --tool toolchain-gccarmnoneeabi
echo "::endgroup::"

echo "::group::Teensy"
echo "\e[32mInstalling the Teensy Core \e[0m"
pio pkg install -g --platform teensy
pio pkg install -g --tool framework-arduinoteensy
pio pkg install -g --tool toolchain-gccarmnoneeabi-teensy
echo "::endgroup::"

echo "::group::Upgrade All Packages"
echo "\e[32m\nUpgrading all installed packages: \e[0m"
pio pkg update
echo "::endgroup::"

echo "::group::Package List"
echo "\e[32m\nCurrently installed packages:\e[0m"
pio pkg list -g -v
echo "::endgroup::"
