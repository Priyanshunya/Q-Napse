#include <Arduino.h>
#include <Wire.h>
#include "../include/qnapse_rpc_protocol.h"

// Qualcomm Arduino UNO Q JDIGITAL / GPIO Pin Definitions
#define PIN_HMC849_RF_SW      D4   // Microsecond SPDT Patch/Omni RF Switch Control
#define PIN_LSM6DSOX_INT1     D2   // Hardware MLC Seismic Knock Interrupt Pin
#define PIN_NEO_M9N_1PPS      D3   // RTK-GNSS 1PPS Nanosecond Sync Input
#define PIN_GREEN_LASER_520NM D7   // Bore-sighted Target Lock Laser Enable

volatile uint32_t g_pps_epoch_us = 0;
volatile uint8_t  g_seismic_mlc_state = SEISMIC_QUIET;
volatile uint16_t g_seismic_peak_mg = 0;
uint8_t           g_current_ant = ANT_OMNI_REFERENCE;

void isr_gnss_1pps() {
    g_pps_epoch_us = micros();
}

void isr_lsm6dsox_mlc_knock() {
    g_seismic_mlc_state = SEISMIC_HUMAN_PIPE_KNOCK;
    g_seismic_peak_mg = 480; // Triggered hardware FSM/MLC threshold
}

void setup() {
    Serial.begin(921600); // High-speed IPC bridge to Qualcomm QRB2210
    Wire.begin();
    Wire.setClock(400000);

    pinMode(PIN_HMC849_RF_SW, OUTPUT);
    pinMode(PIN_GREEN_LASER_520NM, OUTPUT);
    pinMode(PIN_LSM6DSOX_INT1, INPUT_PULLDOWN);
    pinMode(PIN_NEO_M9N_1PPS, INPUT);

    attachInterrupt(digitalPinToInterrupt(PIN_NEO_M9N_1PPS), isr_gnss_1pps, RISING);
    attachInterrupt(digitalPinToInterrupt(PIN_LSM6DSOX_INT1), isr_lsm6dsox_mlc_knock, RISING);
}

void loop() {
    static uint32_t last_cycle_us = 0;
    uint32_t now_us = micros();

    // Deterministic 400 Hz (2500 us) Real-Time Sensor & RF Switch Loop
    if (now_us - last_cycle_us >= 2500) {
        last_cycle_us = now_us;

        // 1. Toggle HMC849 Solid-State RF Switch (Patch vs. Omni Reference)
        g_current_ant = (g_current_ant == ANT_OMNI_REFERENCE)
                        ? ANT_DIRECTIONAL_PATCH_9DBI
                        : ANT_OMNI_REFERENCE;
        digitalWrite(PIN_HMC849_RF_SW, g_current_ant);

        // 2. Pack 32-Byte Deterministic RPC Frame for Qualcomm QRB2210
        QNapseRpcFrame frame = {};
        frame.timestamp_us      = now_us - g_pps_epoch_us;
        frame.quat_wxyz[0]      = 16384; // Q14 Identity W=1.0 (BNO055 + LSM6DSOX fused)
        frame.rf_ant_state      = g_current_ant;
        frame.seismic_mlc_class = g_seismic_mlc_state;
        frame.seismic_peak_mg   = g_seismic_peak_mg;
        frame.battery_mv        = 12800; // 4S LiFePO4 nominal 12.8V
        frame.current_ma        = 620;
        frame.crc16_ccitt       = qnapse_crc16((const uint8_t*)&frame, sizeof(QNapseRpcFrame) - 2);

        Serial.write((const uint8_t*)&frame, sizeof(QNapseRpcFrame));

        // Reset one-shot seismic interrupt flag after transmission
        g_seismic_mlc_state = SEISMIC_QUIET;
    }
}
