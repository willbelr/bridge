//#define DEBUG
#define BRIDGE_ADDRESS 0 
#define RFLIGHT_ADDRESS 3
#define PAIRING 0
#define RXTX 1

#include "DebugUtils.h"
#include <RHReliableDatagram.h>
#include <RH_NRF24.h>
#include <SPI.h>
#include <EEPROM.h>

const byte redLED = A4;
const byte greenLED = A5;
const byte B1PIN = 5;
const unsigned long timeoutInterval = 30*1000L;
const unsigned int pingInterval = 30000;
const unsigned int ledInterval = 600;
const unsigned int ledTimeout = 25;
const unsigned int pairingTimeout = 6000; //10000
unsigned long previousTimeoutInterval;
unsigned long previousPingInterval;
unsigned long previousLedInterval;
unsigned long previousLedTimeout;
unsigned long previousPairingTimeout;
unsigned int ping;
uint8_t clientId = EEPROM.read(1);
uint8_t state = PAIRING;

RH_NRF24 nrf24;
RHReliableDatagram manager(nrf24, BRIDGE_ADDRESS);

int main(void)
{
	init();
	{
		Serial.begin(9600);
		Serial.setTimeout(150);
		Serial.println(F("BRIDGE"));
		
		pinMode(redLED, OUTPUT); digitalWrite(redLED, LOW);
		pinMode(greenLED, OUTPUT); digitalWrite(greenLED, LOW);
	    pinMode(B1PIN, INPUT_PULLUP);
		if (!manager.init()) DEBUG_PRINTLN("init failed");
	}
	while(1)
	{
		if (state == PAIRING)
		{
			if (millis() - previousPairingTimeout >= pairingTimeout)
			{
				state = RXTX;
			}
			if (millis() - previousLedInterval >= ledInterval)
			{
				digitalLow(greenLED);
				digitalWrite(redLED, !digitalState(redLED));
	    		previousLedInterval = millis();
			}

		}
		else if (state == RXTX)
		{
			serial_listen();
			//rf_ping();

	    	if (digitalRead(B1PIN) == LOW)
	    	{
	    		previousPairingTimeout = millis();
	    		state = PAIRING;
	    	}
		}

		rf_listen();
		if (millis() - previousLedTimeout >= ledTimeout)
		{
			digitalLow(greenLED);
		}
	}
	return 0;
}

void serial_listen()
{
int i = 0;
	if (Serial.available())
	{
		char c;
		char serial_data[RH_NRF24_MAX_MESSAGE_LEN] = {0};
		while (Serial.available() > 0) //Read string
		{
			c = Serial.read();
			while (c != '\n')
			{
				if (c != (char)-1)
				{
					serial_data[i] = c;
					i++;
				}
			c = Serial.read();
			}
		}
		rf_sendString(serial_data); //Repeat string to controller
	}
}

void rf_listen()
{
	if (manager.available())
	{
		uint8_t rf_buf[RH_NRF24_MAX_MESSAGE_LEN];
		uint8_t len = sizeof(rf_buf);
		uint8_t from;
		
		if (manager.recvfromAck(rf_buf, &len, &from))
		{
			if (state == RXTX)
			{
				if (from == clientId && strcmp((char*)rf_buf, "ping"))
				{
					ping = 0;
					previousPingInterval = millis();
					Serial.print(from, HEX); Serial.print(";"); Serial.println((char*)rf_buf);
					digitalWrite(redLED, LOW);
					digitalWrite(greenLED, HIGH);
					previousLedTimeout = millis();
				}

			}
			else if (state == PAIRING)
			{
				Serial.print("Paired with "); Serial.println(from, HEX);
				clientId = from;
				EEPROM.write(1, from);
				digitalLow(redLED);
				state = RXTX;
			}
		}
	}
}

void rf_sendString(char str[RH_NRF24_MAX_MESSAGE_LEN])
{
    uint8_t rf_data[RH_NRF24_MAX_MESSAGE_LEN];
    strcpy((char*)rf_data, str); 
    manager.sendtoWait(rf_data, sizeof(rf_data), clientId);
    manager.sendtoWait(rf_data, sizeof(rf_data), RFLIGHT_ADDRESS);
	if (strcmp((char*)rf_data, "ping")) { Serial.print(F("b;")); Serial.println((char*)rf_data); }
}

void rf_ping()
{
	if (millis() - previousPingInterval >= pingInterval)
	{
		previousPingInterval = millis();
		ping++;
		rf_sendString("ping");
		digitalWrite(redLED, HIGH); delay(50); digitalWrite(redLED, LOW);
	}
}
