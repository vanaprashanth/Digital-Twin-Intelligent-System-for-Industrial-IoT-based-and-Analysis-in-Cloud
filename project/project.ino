/**************************************************************************
 Class: ECE508 Spring 2024
 Student Name: Saiprashanth Vana
 Gnumber: G01445432 
 Date: 04/01/2024
 HW: hwLec[08] 
 Description: Arduino code that reads temperature and humidity data from a DHT22 sensor and publishes the readings to an MQTT protocol.
 Issues: No issues
  **************************************************************************/
#include <stdio.h>
#include "myiot33_library.h"  
#include <WiFiNINA.h>
#include <MQTT.h>
#include <DHT.h>

// DHT22 Settings
#define DHTPIN 5 
#define DHTTYPE DHT22 
DHT dht(DHTPIN, DHTTYPE);

const int pirSensorPin = 2; // PIR sensor connected to digital pin 2

const char gNumber[15] = "Gxxxx5432";  
const char ssid[31] = "poor wifi";
const char pass[31] = "idontknow@3999"; 
const char mqttBroker[63] = "192.168.1.173"; 


// MQTT variables
char mqttClienName[31] = "client_59999_Gxxxx5432"; 
int intervalMQTT = 0;
long nmrMqttMesages = 0;
String mqttStringMessage;

// MQTT Topics
String topic;


// Other variables
unsigned long currMillis, prevMillis;

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
  while (!mqttClient.connect(mqttClienName )) { 
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
  

  dht.begin();


  prevMillis = millis();
  int status = WL_IDLE_STATUS;
  while (status != WL_CONNECTED) {
    status = WiFi.begin(ssid, pass);
    delay(250);
  }


  delay(500);

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

  currMillis = millis();
  if (currMillis - prevMillis > 1000) {
    prevMillis = currMillis;

    intervalMQTT++;
    if (intervalMQTT == 5) { 
      intervalMQTT = 0;
      nmrMqttMesages++;

      // Read DHT22 sensor data
      float tempF = dht.readTemperature(true);
      float humidity = dht.readHumidity();
      Serial.println(tempF);
      

      // Publish to MQTT
      String tempString = "type=temp&value="+String(tempF);
      String humidString = "type=humid&value="+String(humidity);
      mqttClient.publish(topic.c_str(), (tempString.c_str()));
      mqttClient.publish(topic.c_str(), (humidString.c_str()));


      // Read PIR sensor data
      int pirValue = digitalRead(pirSensorPin);

      // Publish PIR sensor data to MQTT
      String pirString = "type=pir&value=" + String(pirValue);
      mqttClient.publish(topic.c_str(), pirString.c_str());
      
    }

  }
}