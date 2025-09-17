#!/bin/bash

# Set options,
set -e # Exit with nonzero exit code if anything fails
if [ "$RUNNER_DEBUG" = "1" ]; then
    echo "Enabling debugging!"
    set -v # Prints shell input lines as they are read.
    set -x # Print command traces before executing command.
fi

echo "\e[32mCurrent Arduino CLI version:\e[0m"
arduino-cli version

echo "\e[32mUpdating the core index\e[0m"
arduino-cli --config-file arduino_cli.yaml core update-index

echo "::group::Installing EnviroDIY Cores"
echo "\e[32mInstalling the EnviroDIY AVR Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install EnviroDIY:avr
echo "::endgroup::"

echo "::group::Arduino AVR"
echo "\e[32mInstalling the Arduino AVR Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:avr
echo "::endgroup::"

echo "::group::Arduino SAM"
echo "\e[32mInstalling the Arduino SAM Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:sam
echo "::endgroup::"

echo "::group::Arduino SAMD"

echo "\e[32mInstalling the Arduino SAMD Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:samd
echo "::endgroup::"

echo "::group::Arduino MegaAVR"
echo "\e[32mInstalling the Arduino Mega AVR Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:megaavr
echo "::endgroup::"

echo "::group::Arduino ESP32"
echo "\e[32mInstalling the Arduino ESP32 Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:esp32
echo "::endgroup::"

echo "::group::Arduino Raspberry Pi Pico"
echo "\e[32mInstalling the Arduino RPi Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:mbed_rp2040
echo "::endgroup::"

echo "::group::Arduino Renesas UNO"
echo "\e[32mInstalling the Arduino Renesas Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:renesas_uno
echo "::endgroup::"

echo "::group::Arduino Mbed Nano"
echo "\e[32mInstalling the Arduino Mbed Nano Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:mbed_nano
echo "::endgroup::"

echo "::group::Arduino mBed 32"
echo "\e[32mInstalling the Arduino mBed 32 Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:mbed_portenta
echo "::endgroup::"

echo "::group::Adafruit AVR"
echo "\e[32mInstalling the Adafruit AVR Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install adafruit:avr
echo "::endgroup::"

echo "::group::Adafruit SAMD"
echo "\e[32mInstalling the Adafruit SAMD Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install adafruit:samd
echo "::endgroup::"

echo "::group::Adafruit NRF52"
echo "\e[32mInstalling the Adafruit NRF52 Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install adafruit:nrf52
echo "::endgroup::"

echo "::group::STM32"
echo "\e[32mInstalling the Generic STM32 Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install STMicroelectronics:stm32
echo "::endgroup::"

echo "::group::Espressif ESP8266"
echo "\e[32mInstalling the ESP8266 Arduino Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install esp8266:esp8266
echo "::endgroup::"

echo "::group::Espressif ESP32"
echo "\e[32mInstalling the ESP32 Arduino Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install esp32:esp32
echo "::endgroup::"

echo "::group::Raspberry Pi Pico"
echo "\e[32mInstalling the Raspberry Pi Pico Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install rp2040:rp2040
echo "::endgroup::"

echo "::group::Teensy"
echo "\e[32mInstalling the Teensy Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install teensy:avr
echo "::endgroup::"

echo "\e[32mUpdating the core index\e[0m"
arduino-cli --config-file arduino_cli.yaml core update-index

echo "\e[32mUpgrading all cores\e[0m"
arduino-cli --config-file arduino_cli.yaml core upgrade

echo "\e[32mCurrently installed cores:\e[0m"
arduino-cli --config-file arduino_cli.yaml core list
