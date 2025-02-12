/**************************************************************************
 Class: ECE508 Spring 2024
 Student Name: Saiprashanth Vana and Anurag Josyula 
 Gnumber: G01445432 
 Date: 05/06/2024
 HW: Final Project
 Description: Arduino code that reads data from an ADXL345 accelerometer sensor and a Hall sensor and publishes the readings to an MQTT protocol.
 Issues: No issues
**************************************************************************/

#include <stdio.h>
#include "myiot33_library.h"  
#include <WiFiNINA.h>
#include <MQTT.h>
#include <Wire.h> // Include the Wire library for I2C communication
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL345_U.h> // Include the ADXL345 accelerometer sensor library

// Hall Sensor Settings
const int hallSensorPin = 3; // Hall sensor connected to digital pin 3

const char gNumber[15] = "Gxxxx5432 and Gxxxx2375";  
const char ssid[31] = "poor wifi";
const char pass[31] = "idontknow@3999"; 
const char mqttBroker[63] = "192.168.1.173"; 

// MQTT variables
char mqttClienName[31] = "client_59999_Gxxxx5432"; 
int intervalMQTT = 0;
long nmrMqttMesages = 0;
String mqttStringMessage;

// MQTT Topics
String topic = "/gmu/prashanth/project/topic";

// ADXL345 sensor object
Adafruit_ADXL345_Unified accel = Adafruit_ADXL345_Unified(12345); // Unique ID for I2C communication

WiFiClient wifiClient;
MQTTClient mqttClient;

void messageReceived(String &topic, String &payload){
  Serial.println("incoming: " + topic + " - " + payload);
}

void connectMqtt(char *mqttClienName)  {
  Serial.println("Connecting to WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(1000);
  }
  Serial.println("WiFi Connected!");

  Serial.println("Connecting to MQTT...");
  while (!mqttClient.connect(mqttClienName)) { 
    Serial.print(".");
    delay(1000);
  }
  Serial.println("MQTT Connected!");
}

void setup() {
  Serial.begin(115200);
  randomSeed(analogRead(A7));

  // Generate somewhat-unique MQTT ClientID
  int myRand = random(0, 9999);
  sprintf(mqttClienName, "client_%04d_%s", myRand, gNumber);

  // Build MQTT topics 
  topic = "/gmu/prashanth/project/topic";
  pinMode(3,INPUT);


  // Initialize the ADXL345 sensor
  if(!accel.begin()) {
    Serial.println("Ooops, no ADXL345 detected ... Check your wiring!");
    
  }

  
  // Connect to WiFi
  int status = WL_IDLE_STATUS;
  while (status != WL_CONNECTED) {
    status = WiFi.begin(ssid, pass);
    delay(250);
  }

  // Connect to MQTT broker
  mqttClient.begin(mqttBroker, wifiClient);
  mqttClient.onMessage(messageReceived);
  connectMqtt(mqttClienName); 
}

void loop() {
  mqttClient.loop();

  if (!mqttClient.connected()) {
    connectMqtt(mqttClienName); 
  }

  intervalMQTT++;
  if (intervalMQTT == 5) { 
    intervalMQTT = 0;
    nmrMqttMesages++;

    // Read data from the ADXL345 sensor
    sensors_event_t event;
    accel.getEvent(&event);
    float accelX = event.acceleration.x;
    float accelY = event.acceleration.y;
    float accelZ = event.acceleration.z;

    Serial.print("Accelerometer X: ");
    Serial.print(accelX);
    Serial.print(", Y: ");
    Serial.print(accelY);
    Serial.print(", Z: ");
    Serial.println(accelZ);

    // Read data from the Hall sensor
    int hallValue = digitalRead(hallSensorPin);

    Serial.println(hallValue);

    // Publish accelerometer data to MQTT
    String accelString = "type=accel&value=" + String(accelX) + "," + String(accelY) + "," + String(accelZ);
    mqttClient.publish(topic.c_str(), accelString.c_str());

    // Publish Hall sensor value to MQTT
    String hallString = "type=hall&value=" + String(hallValue);
    mqttClient.publish(topic.c_str(), hallString.c_str());
  }

  delay(1000); // Wait for 1 second
}


1124
3235
oct 7
11124
300
50
300
650
3700 germantownroad
terry

