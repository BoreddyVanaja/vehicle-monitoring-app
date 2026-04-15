#include <LiquidCrystal_I2C.h>
#include <HX711.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

/* -------- PIN DEFINITIONS -------- */
#define LC_DATA_PIN 26
#define LC_SCLK_PIN 27
#define MOSFET_PIN  25
#define LED_PIN     33
#define POWER_PIN   32

/* -------- LOAD LIMIT -------- */
#define LOAD_LIMIT 100   // g

/* OTHER CONSTANTS */
#define CALIBRATION_FACTOR 1010.0f
#define VEHICLE_NUMBER "AP 39 AA 1234"

/* -------- WIFI CREDENTIALS -------- */
const char* ssid = "Manjunath";
const char* password = "12345678";

/* -------- MQTT BROKER -------- */
const char* mqtt_server = "broker.hivemq.com";
WiFiClient espClient;
PubSubClient client(espClient);

/* -------- OBJECTS -------- */
LiquidCrystal_I2C lcd(0x27, 16, 2);
HX711 scale;
JsonDocument data;

// Global variables
String jsonData = "";
float loadValue;
bool isPowerOff = true;

/* -------- MQTT CONNECT FUNCTION -------- */
void connectMQTT() {
  while (!client.connected()) {
    if (client.connect("ESP32_Vehicle_Load_01")) {
    } else {
      delay(1000);
    }
  }
}

/* -------- SETUP -------- */
void setup() {

  lcd.init();
  lcd.backlight();

  pinMode(LED_PIN, OUTPUT);
  pinMode(MOSFET_PIN, OUTPUT);
  pinMode(POWER_PIN, INPUT);

  digitalWrite(LED_PIN, LOW);
  digitalWrite(MOSFET_PIN, HIGH);

  scale.begin(LC_DATA_PIN, LC_SCLK_PIN);
  scale.set_scale(CALIBRATION_FACTOR);
  scale.tare();

  /* -------- WIFI CONNECTION -------- */
  WiFi.begin(ssid, password);
  data["vehicle_number"] = VEHICLE_NUMBER;
  lcd.setCursor(0,0);
  lcd.print("Connecting WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  lcd.clear();
  lcd.print("WiFi Connected");
  delay(1000);

  /* -------- MQTT SETUP -------- */
  client.setServer(mqtt_server, 1883);
  connectMQTT();
}

/* -------- LOOP -------- */
void loop() {

  if (!client.connected()) {
    connectMQTT();
  }
  client.loop();

  lcd.clear();

  isPowerOff = digitalRead(POWER_PIN);

  loadValue = scale.get_units(5);
  if (loadValue < 0) loadValue = 0;

  lcd.setCursor(0,0);
  lcd.print("Load: ");
  lcd.print(loadValue);
  lcd.print("g");

  data["weight"] = loadValue;

  if (loadValue > LOAD_LIMIT) {
    lcd.setCursor(0,1);
    lcd.print("OVERLOAD!");
    
    digitalWrite(LED_PIN, HIGH);
    if(isPowerOff)
    digitalWrite(MOSFET_PIN, LOW);

    data["status"] = "OVERLOAD";
  } 
  else {
    lcd.setCursor(0,1);
    lcd.print("Normal Load");

    digitalWrite(LED_PIN, LOW);
    digitalWrite(MOSFET_PIN, HIGH);

    data["status"] = "NORMAL";
  }

  serializeJson(data,jsonData);
  client.publish("esp32MyProject/data", jsonData.c_str());

  delay(1000);
}
