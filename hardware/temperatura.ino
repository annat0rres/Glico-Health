#include <WiFi.h> // permite a conexão a uma rede wi-fi
#include <HTTPClient.h> // pro esp fazer requisições HTTP
#include <WiFiClientSecure.h> // criptografa com TLS a conexao HTTP (pra ficar HTTPS)
#include <math.h> // pra usar o log 

// configurações da rede 
const char* SECRET_SSID = "Hellen";
const char* SECRET_PASS = "vivi@0204";

// url do vercel (página do pé diabético)
const char* serverName = "https://glico-health.vercel.app/pediabetico";

// pinos
#ifndef LED_BUILTIN
#define LED_BUILTIN 48
#endif
const int pinoLED = LED_BUILTIN; // led embutido no esp

struct SensorNTC {
  const char* id;
  const char* nome;
  int pino;
};

const SensorNTC sensores[] = {
  {"dedao", "Dedão", 4},
  {"metatarso_3", "3º metatarso", 6},
  {"metatarso_5", "5º metatarso", 7},
  {"meio_pe", "Meio do pé", 5},
  {"calcanhar", "Calcanhar", 8}
};
const size_t quantidadeSensores = sizeof(sensores) / sizeof(sensores[0]);

// configurações
// Cada NTC fica entre o GPIO e o GND, com um resistor fixo de 100k entre 3V3 e o GPIO.
const float resistor = 100000.0;  // resistencia do resistor (100KOhm)
const float coef_beta = 3950.0;   // coeficiente beta do NTC
const float resist_ntc = 100000.0;  // resistência do ntc em temperatura ambiente = resistência nominal 
const float temp_ambiente_kelvin = 298.15; // 25°C em Kelvin

void setup() {
  Serial.begin(115200);

  analogReadResolution(12);
  for (size_t i = 0; i < quantidadeSensores; i++) {
    pinMode(sensores[i].pino, INPUT);
    analogSetPinAttenuation(sensores[i].pino, ADC_11db);
  }

  // configura o led embutido
  pinMode(pinoLED, OUTPUT);
  digitalWrite(pinoLED, HIGH); 

  Serial.print("A conectar ao Wi-Fi...");
  WiFi.begin(SECRET_SSID, SECRET_PASS);

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

bool lerTemperaturaNTC(int pino, float& temperatura) {
  uint32_t tensaoMilliVolts = analogReadMilliVolts(pino); // tensão no pino analógico
  if (tensaoMilliVolts == 0 || tensaoMilliVolts >= 3000) return false;

  float vOut = tensaoMilliVolts / 1000.0;
  float rNTC = resistor * (3.3 / vOut - 1.0);

  // equação de Steinhart-Hart / beta
  float steinhart;
  steinhart = rNTC / resist_ntc;              
  steinhart = log(steinhart);         
  steinhart /= coef_beta;                  
  steinhart += 1.0 / temp_ambiente_kelvin;              
  steinhart = 1.0 / steinhart;        
  steinhart -= 273.15; // converte para Celsius

  if (!isfinite(steinhart)) return false;
  temperatura = steinhart;
  return true;
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    // configura o cliente seguro para ignorar validação de SSL estrita da Vercel
    WiFiClientSecure client;
    client.setInsecure();

    HTTPClient http;
    http.begin(client, serverName);
    http.addHeader("Content-Type", "application/json");

    float temperaturas[quantidadeSensores];
    float maiorTemp = -999.0; // começa bem baixo para ser substituído na primeira leitura
    float menorTemp = 999.0;  // começa bem alto para ser substituído na primeira leitura
    bool leituraValida = true;

    for (size_t i = 0; i < quantidadeSensores; i++) {
      if (!lerTemperaturaNTC(sensores[i].pino, temperaturas[i])) {
        Serial.printf("Leitura inválida no sensor %s (GPIO %d)\n", sensores[i].nome, sensores[i].pino);
        leituraValida = false;
      } else {
        // atualiza a maior e a menor temperatura encontradas
        if (temperaturas[i] > maiorTemp) maiorTemp = temperaturas[i];
        if (temperaturas[i] < menorTemp) menorTemp = temperaturas[i];
      }
    }

    if (leituraValida) {
      // calcula a diferença entre a maior e a menor temperatura
      float diferencaTemp = maiorTemp - menorTemp;

      // monta o payload em formato JSON
      String jsonPayload = "{\"temperatura\":" + String(temperaturas[0], 2) + ",\"sensores\":{";
      for (size_t i = 0; i < quantidadeSensores; i++) {
        if (i > 0) jsonPayload += ",";
        jsonPayload += "\"" + String(sensores[i].id) + "\":" + String(temperaturas[i], 2);
      }
      jsonPayload += "}}";

      // pisca rápido o led para avisar o momento do envio
      digitalWrite(pinoLED, HIGH); // apaga rapidamente
      delay(100);
      digitalWrite(pinoLED, LOW);  // acende novamente

      int httpResponseCode = http.POST(jsonPayload);

      if (httpResponseCode >= 200 && httpResponseCode < 300) {
        Serial.printf("Cinco sensores enviados | Diferença (Máx - Mín): %.2f °C (Máx: %.2f °C / Mín: %.2f °C) | Código HTTP: %d\n",
                      diferencaTemp, maiorTemp, menorTemp, httpResponseCode);
      } else if (httpResponseCode > 0) {
        String resposta = http.getString();
        Serial.printf("Erro HTTP %d: %s\n", httpResponseCode, resposta.c_str());
      } else {
        Serial.printf("Erro ao enviar: %s\n", http.errorToString(httpResponseCode).c_str());
      }
    } else {
      Serial.println("Envio cancelado: verifique as conexões dos sensores NTC.");
    }
    http.end();
  } else {
    // se perder o wi-fi, apaga o led
    digitalWrite(pinoLED, HIGH);
  }

  delay(10000); // envia o dado a cada 10 segundos
}
