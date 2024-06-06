#!/bin/bash

# Set options,
set -e # Exit with nonzero exit code if anything fails
set -v # Prints shell input lines as they are read.
set -x # Print command traces before executing command.

echo "\n\e[32mCurrent Arduino CLI version:\e[0m"
arduino-cli version

echo "\n\e[32mUpdating the core index\e[0m"
arduino-cli --config-file arduino_cli.yaml core update-index

echo "::group::Installing EnviroDIY Cores"
echo "\n\e[32mInstalling the EnviroDIY AVR Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install EnviroDIY:avr
echo "::endgroup::"

echo "::group::Installing Arduino Official Cores"
echo "\n\e[32mInstalling the Arduino AVR Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:avr

echo "\n\e[32mInstalling the Arduino Mega AVR Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:megaavr

echo "\n\e[32mInstalling the Arduino SAM Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:sam

echo "\n\e[32mInstalling the Arduino SAMD Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:samd

echo "\n\e[32mInstalling the Arduino ESP32 Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:esp32

echo "\n\e[32mInstalling the Arduino RPi Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:mbed_rp2040

echo "\n\e[32mInstalling the Arduino Renesas Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install arduino:renesas_uno
echo "::endgroup::"

echo "::group::Installing Adafruit Cores"
echo "\n\e[32mInstalling the Adafruit SAMD Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install adafruit:samd
echo "::endgroup::"

echo "::group::Installing Espressif Cores"
echo "\n\e[32mInstalling the ESP8266 Arduino Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install esp8266:esp8266

echo "\n\e[32mInstalling the ESP32 Arduino Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install esp32:esp32
echo "::endgroup::"

echo "::group::Installing RPi Cores"
echo "\n\e[32mInstalling the Raspberry Pi Pico Arduino Core\e[0m"
arduino-cli --config-file arduino_cli.yaml core install rp2040:rp2040
echo "::endgroup::"

echo "\n\e[32mUpdating the core index\e[0m"
arduino-cli --config-file arduino_cli.yaml core update-index

echo "\n\e[32mUpgrading all cores\e[0m"
arduino-cli --config-file arduino_cli.yaml core upgrade

echo "\n\e[32mCurrently installed cores:\e[0m"
arduino-cli --config-file arduino_cli.yaml core list
