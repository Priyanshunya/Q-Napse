#ifndef QNAPSE_RPC_PROTOCOL_H
#define QNAPSE_RPC_PROTOCOL_H

#include <stdint.h>

#pragma pack(push, 1)

enum RfAntennaState : uint8_t {
    ANT_OMNI_REFERENCE = 0x00,
    ANT_DIRECTIONAL_PATCH_9DBI = 0x01
};

enum SeismicMlcClass : uint8_t {
    SEISMIC_QUIET = 0x00,
    SEISMIC_HUMAN_PIPE_KNOCK = 0x01,
    SEISMIC_EXCAVATOR_NOISE = 0x02,
    SEISMIC_STRUCTURAL_SHIFT = 0x03
};

struct QNapseRpcFrame {
    uint32_t timestamp_us;        // 1PPS-disciplined microsecond timestamp
    int16_t  quat_wxyz[4];        // Q14 fixed-point quaternion (BNO055 + LSM6DSOX 400Hz)
    uint8_t  rf_ant_state;        // HMC849 SPDT switch state (0=Omni, 1=Patch)
    uint8_t  seismic_mlc_class;   // LSM6DSOX hardware MLC interrupt state
    uint16_t seismic_peak_mg;     // Peak 20-150Hz P/S-wave acceleration (milli-g)
    uint16_t battery_mv;          // INA226 7-24V input rail voltage (mV)
    uint16_t current_ma;          // INA226 current draw (mA)
    uint8_t  can_uav_status[10];  // MAVLink / UAVCAN telemetry bytes
    uint16_t crc16_ccitt;         // Frame integrity checksum
};

#pragma pack(pop)

static inline uint16_t qnapse_crc16(const uint8_t* data, uint16_t length) {
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < length; ++i) {
        crc ^= (uint16_t)data[i] << 8;
        for (uint8_t j = 0; j < 8; ++j) {
            crc = (crc & 0x8000) ? ((crc << 1) ^ 0x1021) : (crc << 1);
        }
    }
    return crc;
}

#endif // QNAPSE_RPC_PROTOCOL_H
