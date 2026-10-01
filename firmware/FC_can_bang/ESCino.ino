// setup_motor
// test_motor
// control_motor 
// calip_motor

#define esc_1_pin 27
#define esc_2_pin 26
#define esc_3_pin 25 
#define esc_4_pin 33

const int esc_channel_1 = 0, esc_channel_2 = 1, esc_channel_3 = 2, esc_channel_4 = 3, esc_channel_5 = 4, esc_channel_6 = 5;

const int freq = 391;  ////tương ứng 800 1600 ->1000 2000 
const int resolution = 11;

unsigned long time_start_test_motor_1;
unsigned long time_start_test_motor_2;
unsigned long time_start_test_motor_3;
unsigned long time_start_test_motor_4;
int time_test_motor = 2000;

int value_test_motor_1;
int value_test_motor_2;
int value_test_motor_3;
int value_test_motor_4;

void setup_motor() {
  ledcSetup(esc_channel_1, freq, resolution); ledcAttachPin(esc_1_pin, esc_channel_1);
  ledcSetup(esc_channel_2, freq, resolution); ledcAttachPin(esc_2_pin, esc_channel_2);
  ledcSetup(esc_channel_3, freq, resolution); ledcAttachPin(esc_3_pin, esc_channel_3);
  ledcSetup(esc_channel_4, freq, resolution); ledcAttachPin(esc_4_pin, esc_channel_4);

}


void control_motor( int esc_1, int esc_2, int esc_3, int esc_4, bool arm) {

  if( status_arm == 1) {
    ledcWrite(esc_channel_1, esc_1); // esc_1 ở đây là giá trị sau khi trộn motor
    ledcWrite(esc_channel_2, esc_2);
    ledcWrite(esc_channel_3, esc_3);
    ledcWrite(esc_channel_4, esc_4);
  } else {
    if( millis() - time_start_test_motor_1 < time_test_motor){
      ledcWrite( esc_channel_1, value_test_motor_1);
    } else { 
      ledcWrite( esc_channel_1, 800);
    }
    if( millis() - time_start_test_motor_2 < time_test_motor){
      ledcWrite( esc_channel_2, value_test_motor_2);
    } else { 
      ledcWrite( esc_channel_2, 800);
    }
    if( millis() - time_start_test_motor_3 < time_test_motor){
      ledcWrite( esc_channel_3, value_test_motor_3);
    } else { 
      ledcWrite( esc_channel_3, 800);
    }
    if( millis() - time_start_test_motor_4 < time_test_motor){
      ledcWrite( esc_channel_4, value_test_motor_4);
    } else { 
      ledcWrite( esc_channel_4, 800);
    }
  }
}










