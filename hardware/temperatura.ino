#include <ESP8266WiFi.h> // permite a conexão a uma rede wi-fi
#include <ESP8266HTTPClient.h> // pro esp fazer requisições HTTP
#include <WiFiClientSecureBearSSL.h> // criptografa com TLS a conexao HTTP (pra ficar HTTPS)
#include <math.h> // pra usar o log 

// configurações da rede 
#include "secrets.h"

// url do vercel (página do pé diabético)
const char* serverName = "https://glico-health.vercel.app/pediabetico";

// pinos
const int pinoLED = LED_BUILTIN; // led embutido no esp
const int pinoNTC = A0;          // pino analógico

// configurações
const float resistor = 100000.0;  // resistencia do resistor (100KOhm)
const float coef_beta = 3950.0;   // coeficiente beta do NTC
const float resist_ntc = 100000.0;  // resistência do ntc em temperatura ambiente = resistência nominal 
const float temp_ambiente_kelvin = 298.15; // 25°C em Kelvin

void setup() {
  Serial.begin(115200);

  // configura o led embutido
  pinMode(pinoLED, OUTPUT);
  digitalWrite(pinoLED, HIGH); 

  Serial.print("A conectar ao Wi-Fi...");
  WiFi.begin(ssid, password);

  // pra piscar o led enquanto tenta conectar
  while (WiFi.status() != WL_CONNECTED) {
    digitalWrite(pinoLED, LOW);   
    delay(250);
    digitalWrite(pinoLED, HIGH);  
    delay(250);
    Serial.print(".");
  }

  Serial.println("\nWi-Fi conectado com sucesso!");
  digitalWrite(pinoLED, LOW); // led aceso direto pra indicar q tá online
}

float lerTemperaturaNTC() {
  int adcVal = analogRead(pinoNTC); // tensão no pino A0
  if (adcVal == 0) return 0.0;

  float vOut = (adcVal / 1023.0) * 3.3; // 1023 é o valor máximo da escala de leitura; 10 bits
  float rNTC = resistor * (3.3 / vOut - 1.0);

  // equação de Steinhart-Hart / beta
  float steinhart;
  steinhart = rNTC / resist_ntc;              
  steinhart = log(steinhart);         
  steinhart /= coef_beta;                  
  steinhart += 1.0 / temp_ambiente_kelvin;              
  steinhart = 1.0 / steinhart;        
  steinhart -= 273.15; // converte para Celsius

  return steinhart;
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    // configura o cliente seguro para ignorar validação de SSL estrita da Vercel
    std::unique_ptr<BearSSL::WiFiClientSecure> client(new BearSSL::WiFiClientSecure);
    client->setInsecure();

    HTTPClient http;
    http.begin(*client, serverName);
    http.addHeader("Content-Type", "application/json");

    float tempC = lerTemperaturaNTC();

    // monta o payload em formato JSON
    String jsonPayload = "{\"temperatura\":" + String(tempC, 2) + "}";

    // pisca rápido o led para avisar o momento do envio
    digitalWrite(pinoLED, HIGH); // apaga rapidamente
    delay(100);
    digitalWrite(pinoLED, LOW);  // acende novamente

    int httpResponseCode = http.POST(jsonPayload);

    if (httpResponseCode > 0) {
      Serial.printf("Enviado com sucesso: %.2f °C | Código HTTP: %d\n", tempC, httpResponseCode);
    } else {
      Serial.printf("Erro ao enviar: %s\n", http.errorToString(httpResponseCode).c_str());
    }
    http.end();
  } else {
    // se perder o wi-fi, apaga o led
    digitalWrite(pinoLED, HIGH);
  }

  delay(10000); // envia o dado a cada 10 segundos
}