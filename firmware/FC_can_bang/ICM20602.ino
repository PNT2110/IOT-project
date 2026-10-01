#include <SPI.h>

#define offset_acc_x +0.0224
#define offset_acc_y +0.0162
#define offset_acc_z -0.0053

#define SPI_CLOCK 1000000
#define PIN_CS 5

#define WHO_AM_I 0x75
#define PWR_MGMT_1 0x6B
#define ACCEL_XOUT_H 0x3B
#define GYRO_XOUT_H 0x43
#define GYRO_CONFIG 0x1B
#define ACCEL_CONFIG 0x1C
#define CONFIG 0x1A
#define ACCEL_CONFIG2 0x1D


SPISettings settings(SPI_CLOCK, MSBFIRST, SPI_MODE0);
// float RateRoll, RatePitch, RateYaw;
// // float Acc_x, Acc_y, Acc_z;
// float AngleRoll, AnglePitch, AngleYaw;

float RateCalibrationRoll_1, RateCalibrationPitch_1, RateCalibrationYaw_1;
float RateCalibrationRoll_2, RateCalibrationPitch_2, RateCalibrationYaw_2;
float RateCalibrationNumber;

float KalmanAngleRoll = 0, KalmanUncertaintyAngleRoll = 2*2;
float KalmanAnglePitch = 0, KalmanUncertaintyAnglePitch = 2*2;


 
void setup_icm20602() {

  // CÀI ĐẶT SPI
  // ĐÁNH THỨC
  // OFFSET

 Serial.setTxBufferSize(2048);   // de gui telemetry khong chan vong 5 ms
 Serial.setRxBufferSize(512);
 Serial.begin(115200);
 SPI.begin();
 pinMode(PIN_CS, OUTPUT);
 digitalWrite(PIN_CS, HIGH);
 
 ICM20620_danhthuc();  // đánh thức

 while(1) {

    // gán giá trị mới thành giá trị cũ
    // lấy 2000 mẫu
    // tính defferent
    // so sánh điều kiện để thoát vòng lặp

     RateCalibrationRoll_2 = RateCalibrationRoll_1;
     RateCalibrationPitch_2 = RateCalibrationPitch_1;
     RateCalibrationYaw_2 = RateCalibrationYaw_1;

     RateCalibrationRoll_1 = 0;
     RateCalibrationPitch_1 = 0;
     RateCalibrationYaw_1 = 0;

     for(RateCalibrationNumber = 0; RateCalibrationNumber < 2000; RateCalibrationNumber++) {

        gyro_signal(); // cập nhật dữ liệu
        RateCalibrationRoll_1 += RateRoll;
        RateCalibrationPitch_1 += RatePitch;
        RateCalibrationYaw_1 += RateYaw;
        delay(1);

     }

      float rate_cali_roll_dif, rate_cali_pitch_dif, rate_cali_yaw_dif;

      rate_cali_roll_dif = fabsf(RateCalibrationRoll_1 - RateCalibrationRoll_2);
      rate_cali_pitch_dif = fabsf(RateCalibrationPitch_1 - RateCalibrationPitch_2);
      rate_cali_yaw_dif = fabsf(RateCalibrationYaw_1 - RateCalibrationYaw_2);

      if(rate_cali_roll_dif < 20 &&
         rate_cali_pitch_dif < 20 &&
         rate_cali_yaw_dif < 20) {

         // calib xong (khong in ra Serial: cong USB chi danh cho frame JSON gui Pi)
         break;
      }
    }

    RateCalibrationRoll_1 /= 2000;
    RateCalibrationPitch_1 /= 2000;
    RateCalibrationYaw_1 /= 2000;

}


void icm20602() {

    // cập nhật dữ liệu
    // chạy vào hàm kalman lọc nhiễu đưa ra dữ liệu tốt

    gyro_signal();

    kalman_1d(
      KalmanAngleRoll,
      KalmanUncertaintyAngleRoll,
      rateroll,
      AngleRoll
    );

    kalman_1d(
      KalmanAnglePitch,
      KalmanUncertaintyAnglePitch,
      ratepitch,
      AnglePitch
    );
}


void ICM20620_danhthuc() {

  writeRegister(PWR_MGMT_1, 0x00);
  delay(100);

  writeRegister(CONFIG, 0x06);

  // ACCEL ±16g
  writeRegister(ACCEL_CONFIG, 0x18);

  // GYRO ±2000 dps
  writeRegister(GYRO_CONFIG, 0x18);

  writeRegister(ACCEL_CONFIG2, 0x05);

  delay(100);
}


void gyro_signal(void) {
 
   // lấy dữ liệu từ gyro
   // lấy dữ liệu từ accel
   // đổi đơn vị gyro
   // đổi đơn vị accel
   // offset Accel
   // tính angle theo acc

    int16_t GYRO_X, GYRO_Y, GYRO_Z;

    readgyro(
      GYRO_X,
      GYRO_Y,
      GYRO_Z
    );


    int16_t acc_x_1, acc_y_1, acc_z_1;

    readaccel(
      acc_x_1,
      acc_y_1,
      acc_z_1
    );


    // ============================================
    // GYRO ±2000 dps
    // 16.4 LSB / dps
    // ============================================

    RateRoll = (float)GYRO_X / 16.4;
    RatePitch = (float)GYRO_Y / 16.4;
    RateYaw = (float)GYRO_Z / 16.4;


    // ============================================
    // ACCEL ±16g
    // 2048 LSB / g
    // ============================================

    Acc_x = (float)acc_x_1 / 2048;
    Acc_y = (float)acc_y_1 / 2048;
    Acc_z = (float)acc_z_1 / 2048;


    Acc_x_bu = Acc_x + offset_acc_x;
    Acc_y_bu = Acc_y + offset_acc_y; 
    Acc_z_bu = Acc_z + offset_acc_z;


    AngleRoll =
      atan(
        Acc_y_bu /
        sqrt(
          Acc_x_bu * Acc_x_bu +
          Acc_z_bu * Acc_z_bu
        )
      )
      * 1 / (3.142 / 180);


    AnglePitch =
      -atan(
        Acc_x_bu /
        sqrt(
          Acc_y_bu * Acc_y_bu +
          Acc_z_bu * Acc_z_bu
        )
      )
      * 1 / (3.142 / 180);

}


void kalman_1d(
  float &KalmanState,
  float &KalmanUncertainty,
  float KalmanInput,
  float KalmanMeasurement
) {

  KalmanState =
    KalmanState +
    0.005 * KalmanInput;

  KalmanUncertainty =
    KalmanUncertainty +
    0.005 * 0.005 * 1 * 1;

  float KalmanGain =
    KalmanUncertainty * 1 /
    (1 * KalmanUncertainty + 3 * 3);

  KalmanState =
    KalmanState +
    KalmanGain *
    (KalmanMeasurement - KalmanState);

  KalmanUncertainty =
    (1 - KalmanGain) *
    KalmanUncertainty;
}


void writeRegister(uint8_t reg, uint8_t value) {

    digitalWrite(PIN_CS, LOW);

    SPI.beginTransaction(settings);

    SPI.transfer(reg & 0x7F);
    SPI.transfer(value);

    SPI.endTransaction();

    digitalWrite(PIN_CS, HIGH);

}


uint8_t readRegister(uint8_t reg) {

    digitalWrite(PIN_CS, LOW);

    SPI.beginTransaction(settings);

    SPI.transfer(reg | 0x80);

    uint8_t value =
      SPI.transfer(0x00);

    SPI.endTransaction();

    digitalWrite(PIN_CS, HIGH);

    return value;

}


void readgyro(
  int16_t &x,
  int16_t &y,
  int16_t &z
) {

    digitalWrite(PIN_CS, LOW);

    SPI.beginTransaction(settings);

    SPI.transfer(GYRO_XOUT_H | 0x80);

    x =
      (SPI.transfer(0x00) << 8 |
       SPI.transfer(0x00));

    y =
      (SPI.transfer(0x00) << 8 |
       SPI.transfer(0x00));

    z =
      (SPI.transfer(0x00) << 8 |
       SPI.transfer(0x00));

    SPI.endTransaction();

    digitalWrite(PIN_CS, HIGH);
}


void readaccel(
  int16_t &x,
  int16_t &y,
  int16_t &z
) {

    digitalWrite(PIN_CS, LOW);

    SPI.beginTransaction(settings);

    SPI.transfer(ACCEL_XOUT_H | 0x80);

    x =
      (SPI.transfer(0x00) << 8 |
       SPI.transfer(0x00));

    y =
      (SPI.transfer(0x00) << 8 |
       SPI.transfer(0x00));

    z =
      (SPI.transfer(0x00) << 8 |
       SPI.transfer(0x00));

    SPI.endTransaction();

    digitalWrite(PIN_CS, HIGH);
}


void volocity_vertical_AccZ() { 

  AccZInertial =
    -sin(anglepitch * (3.142 / 180)) * Acc_x_bu
    +
    cos(anglepitch * (3.142 / 180))
    *
    sin(angleroll * (3.142 / 180))
    *
    Acc_y_bu
    +
    cos(anglepitch * (3.142 / 180))
    *
    cos(angleroll * (3.142 / 180))
    *
    Acc_z_bu;

  AccZInertial =
    (AccZInertial - 1) *
    9.81 *
    100;

  volocity_vertical =
    volocity_vertical +
    0.05 * AccZInertial;
}


float get_Acc_x() {
  return Acc_x;
}

float get_Acc_y() {
  return Acc_y;
}

float get_Acc_z() {
  return Acc_z;
}


float get_RateRoll() {
  return RateRoll - RateCalibrationRoll_1;
}

float get_RatePitch() {
  return RatePitch - RateCalibrationPitch_1;
}

float get_RateYaw() {
  return RateYaw - RateCalibrationYaw_1;
}


float get_AngleRoll() {
  return KalmanAngleRoll;
}

float get_AnglePitch() {
  return KalmanAnglePitch;
}


float get_status() {
  return 1;
}

// ---- Bo sung: nhiet do IMU + yaw tuong doi (tich phan gyro, chua co la ban) ----
#define TEMP_OUT_H 0x41
static float imu_temp_c = NAN;
static unsigned long imu_temp_last_ms = 0;
static float yaw_relative_deg = 0;

void imu_temperature_update() {
  if (millis() - imu_temp_last_ms < 100) return;
  imu_temp_last_ms = millis();
  int16_t raw = (int16_t)((readRegister(TEMP_OUT_H) << 8) | readRegister(TEMP_OUT_H + 1));
  imu_temp_c = raw / 326.8f + 25.0f;   // ICM-20602 datasheet
}

float get_imu_temperature() { return imu_temp_c; }

void yaw_integrate(float rate_dps, float dt) {
  yaw_relative_deg += rate_dps * dt;
  while (yaw_relative_deg > 180) yaw_relative_deg -= 360;
  while (yaw_relative_deg < -180) yaw_relative_deg += 360;
}

float get_YawRelative() { return yaw_relative_deg; }
