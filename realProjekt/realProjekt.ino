#include <SoftwareSerial.h>

#define RELAY_PIN 7  
#define MOISTURE_PIN A0  

SoftwareSerial BTSerial(2, 3);  // RX, TX for Bluetooth communication

void setup() {
  pinMode(RELAY_PIN, OUTPUT);
  Serial.begin(9600);      // Serial communication over USB (for debugging and server communication)
  BTSerial.begin(9600);    // Bluetooth communication

  // Let’s start with sending a message to confirm setup
  Serial.println("Arduino ready, waiting for commands...");
  BTSerial.println("Arduino ready, waiting for commands...");
}

void loop() {
  // Read the moisture sensor
  int moisture = analogRead(MOISTURE_PIN);
  String sensorData = "SENSOR:" + String(moisture);

  // Send sensor data via both USB and Bluetooth
  Serial.println(sensorData);  
  BTSerial.println(sensorData);  // Send via Bluetooth

  // Check if there is any incoming data from Bluetooth
  if (BTSerial.available()) {
    char command = BTSerial.read();
    if (command == '1') {  // Relay ON via Bluetooth
      digitalWrite(RELAY_PIN, LOW);  // Assuming LOW turns ON the relay
      Serial.println("RELAY:ON");
      BTSerial.println("RELAY:ON");
    } else if (command == '0') {  // Relay OFF via Bluetooth
      digitalWrite(RELAY_PIN, HIGH);  // Assuming HIGH turns OFF the relay
      Serial.println("RELAY:OFF");
      BTSerial.println("RELAY:OFF");
    }
  }

  // Check if there is any incoming data from USB (Serial)
  if (Serial.available()) {
    char command = Serial.read();
    if (command == '1') {  // Relay ON via USB
      digitalWrite(RELAY_PIN, LOW);  // Assuming LOW turns ON the relay
      Serial.println("RELAY:ON");
    } else if (command == '0') {  // Relay OFF via USB
      digitalWrite(RELAY_PIN, HIGH);  // Assuming HIGH turns OFF the relay
      Serial.println("RELAY:OFF");
    }
  }

  delay(2000);  // Wait 2 seconds before next reading
}
