
#include <HardwareSerial.h>
HardwareSerial Serial_sbus(2);

#define low_value_filter_roll_pitch 0.1
#define throttle_smoot_value 0.1
#define low_value_filter_roll_yaw 0.1
#define thr_smoot_value 0.1
#define yaw_v_max 90
#define euler_max 10
#define low_value_filter_yaw 0.1

static bool dathudu;
static unsigned int sbusbyte, byteNum;
static byte frame[25];
//static unsigned int sbus_ch[26], channel_sbus[26];
//float roll_target, pitch_target, yaw_vel_target;
unsigned long last_timer_sbus;

bool getframe() {

  // kiểm tra dodgs gói tính hiệu sbus
  // đóng gói tín hiệu 
  //return kết quả để đi giải nén

  while(Serial_sbus.available()) {
    sbusbyte = Serial_sbus.read();
     if(sbusbyte == 0x0F && dathudu) {
      dathudu = false;
      byteNum = 0;
     } else if( sbusbyte == 0) dathudu = true;

     if( byteNum <= 24){
      frame[byteNum] = sbusbyte;
      byteNum++;
     } 
     if ( (byteNum == 25) && (sbusbyte == 0) && (frame[0] == 0x0F)) {return true;}

  }
  return false;
}

void decodesbus() {
  int bytetro = 1;
  int bittro = 0;

  // chia thành 16 kênh mỗi kênh 11 bit
 for(int chan=1; chan<=16; chan++) {
  channel_sbus[chan] = 0;
   for(int chanbit=0; chanbit<11; chanbit++){
     channel_sbus[chan] |= ((frame[bytetro] >> bittro) & 1) << chanbit;

      if(++bittro > 7){
       bittro = 0;
       bytetro++;
      }
    }
  }
}
 
void setup_sbus(){
  Serial_sbus.begin(100000, SERIAL_8E2, 35, -1,true);
  byteNum = 255;
  dathudu = false;

}


unsigned int i;
int readsbus() {
  // kiểm tra tín hiệu sbus
  // map tín hiệu

  if ( getframe()){
    decodesbus();
    for(i=1; i<=16; i++) {
      sbus_ch[i] = map(channel_sbus[i], 178, 1811, 1000, 2000);
    }

    // Bo thu van gui frame khi mat tay dieu khien, nhung bat co failsafe (byte 23, bit 3).
    if (sbus_flags_ok(frame[23])) last_timer_sbus = millis();
  }

  if( millis() - last_timer_sbus > 200) {
      return 0;
  } else { return 1;}
}


int read_data_control()  {
  int status_sbus = readsbus(); // trả về 0 OR 1

    roll_target = roll_target * (1 - low_value_filter_roll_pitch) + (((float)sbus_ch[1] - 1500) / (500.0 / euler_max)) * low_value_filter_roll_pitch;
    pitch_target = pitch_target * (1 - low_value_filter_roll_pitch) + (((float)sbus_ch[2] - 1500) / (500.0 / euler_max)) * low_value_filter_roll_pitch;
    throttle_smoot= throttle_smoot*(1- thr_smoot_value) + map((sbus_ch[3]),1000,2000,800,1600)*thr_smoot_value; // dảy 800 - 1600
    yaw_vel_target = yaw_vel_target * (1 - low_value_filter_yaw) + -(((float)sbus_ch[4] - 1500) / (500.0 / yaw_v_max)) * low_value_filter_yaw; 
    
    rateroll_target = map(sbus_ch[2], 1000, 2000, -200, 200);
    ratepitch_target = map(sbus_ch[1], 1000, 2000, -200, 200);


    if(status_sbus == 0)  {
      roll_target = 0;
      pitch_target = 0;
      throttle_smoot = 800;
    }

    return status_sbus;
}

int ch( int i) { return sbus_ch[i]; }














