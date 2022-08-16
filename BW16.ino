//must install the SoftWire library
#include <WiFi.h>
#include <stdio.h>
#include <wifi_conf.h>
#include "ATcommands.h"
#include <SoftwareSerial.h>
#include "WDT.h" //watchdog library
//have to undefine these arduino definss for the RTL std library
#undef max
#undef min
#include <list>
#define SCAN_CHANNEL_NUM 2 //2.4GHz + 5GHz
u8 scan_channel_list2[SCAN_CHANNEL_NUM] = {6,48};
// define watch dog
#define RUN_CALLBACK_IF_WATCHDOG_BARKS (0)
WDT wdt;

char buffer[256];

struct WiFiSignal {
    unsigned char addr[6]; 
    unsigned short seq;
    signed char rssi;
};

std::list<WiFiSignal> _signals;

const uint32_t address = 0x00002001;
const uint32_t multi_address = 0x00002000;
uint8_t headerState = 0;
uint8_t dataState = 0;
uint32_t readLength = 0;
uint32_t length = 0;
uint32_t readIndex = 0;
uint8_t buff1[1500];
uint8_t buff2[1500];
uint8_t *readData = buff1;
uint8_t *executeData = buff2;
uint32_t executeLength = 0;
uint8_t channel = 2;			// initial Channel
uint8_t tmp = 2;
String inputString = "";         // a String to hold incoming data
bool stringComplete = false;  // whether the string is complete
rtw_result_t wifi_setting_success = RTW_SUCCESS; 

void setup() {
    //Initialize serial and wait for port to open:
    wdt.InitWatchdog(5000);  // setup 5s watchdog
    #if RUN_CALLBACK_IF_WATCHDOG_BARKS
    wdt.InitWatchdogIRQ(my_watchdog_irq_handler, 0);
    #else
        // system would restart in default when watchdog barks
    #endif
    wdt.StartWatchdog();  // enable watchdog timer
    pinMode(LED_R, OUTPUT);
    pinMode(LED_G, OUTPUT);
    pinMode(LED_B, OUTPUT);
    pinMode(PA12, OUTPUT);
    digitalWrite(PA12, LOW);
    pinMode(PB3, OUTPUT);
    digitalWrite(PB3, HIGH);
    Serial.begin(115200);
//    while (!Serial) {
//        ; // wait for serial port to connect. Needed for native USB port only
//    }
    wifi_on(RTW_MODE_PROMISC);
    wifi_rf_on();
    wext_set_bw40_enable(TRUE);
    wifi_set_channel(channel);
    wifi_enter_promisc_mode();
    wifi_set_promisc(RTW_PROMISC_ENABLE_2, promisc_callback, 0);


}



void loop() {
      led_blink();
      if (stringComplete) {
        tmp = inputString.toInt();
        // clear the string:
        inputString = "";
        stringComplete = false;
        wifi_setting_success = wifi_set_channel(tmp);
        if(wifi_setting_success == RTW_SUCCESS){
          channel = tmp;
        }
        wdt.RefreshWatchdog();
      }
}

/*  Make callback simple to prevent latency to wlan rx when promiscuous mode */
static void promisc_callback(unsigned char *buf, unsigned int len, void* userdata)
{
    const ieee80211_frame_info_t *frameInfo = (ieee80211_frame_info_t *)userdata;
	
    if(frameInfo->rssi == 0)
        return;
    WiFiSignal wifisignal;
    wifisignal.rssi = frameInfo->rssi;
    wifisignal.seq = frameInfo->i_seq;
    memcpy(&wifisignal.addr, &frameInfo->i_addr2, 6);
    printMac_RSSI(wifisignal.addr, wifisignal.rssi, wifisignal.seq);
    wdt.RefreshWatchdog();
}


void printMac_RSSI(const unsigned char mac[6], int rssi, short seq) {
    char buff[48];
    sprintf(buff, "CH:%d,MAC:%02X:%02X:%02X:%02X:%02X:%02X,RSSI:%03d,Seq:%d", channel, mac[0], mac[1], mac[2], mac[3], mac[4], mac[5], rssi, seq);
    sprintf(buff, "%02X:%02X:%02X:%02X:%02X:%02X,%03d,%d,%d", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5], rssi, seq, channel);
    Serial.println(buff);
}

void led_blink(){
  delay(2);
}

void serialEvent() {
  while (Serial.available()) {
    // get the new byte:
    char inChar = (char)Serial.read();
    // add it to the inputString:
    inputString += inChar;
    // if the incoming character is a newline, set a flag so the main loop can
    // do something about it:
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
}
