float PIDOutput[]={0,0,0};

float ErrorAngleRoll, ErrorAnglePitch, ErrorAngleYaw;
float PreErrorAngleRoll, PreErrorAnglePitch, PreErrorAngleYaw;

float ItermAngleRoll, ItermAnglePitch, ItermAngleYaw;
float PreItermAngleRoll, PreItermAnglePitch, PreItermAngleYaw;


float ErrorRateRoll, ErrorRatePitch, ErrorRateYaw;
float PreErrorRateRoll, PreErrorRatePitch, PreErrorRateYaw;

float ItermRateRoll, ItermRatePitch, ItermRateYaw;
float PreItermRateRoll, PreItermRatePitch, PreItermRateYaw;

float PAngleRoll = 10;
float IAngleRoll = 0;
float DAngleRoll = 0;

float PAnglePitch = 10;
float IAnglePitch = 0;
float DAnglePitch = 0;

float PAngleYaw = 0;
float IAngleYaw = 0;
float DAngleYaw = 0;

float PRateRoll = 0.4;
float IRateRoll = 0.4;
float DRateRoll = 0.02;

float PRatePitch = 0.4;
float IRatePitch = 0.4;
float DRatePitch = 0.02;

float PRateYaw = 1;
float IRateYaw = 10;
float DRateYaw = 0;

//float INPUTROLL;
///float INPUTPITCH;
//float INPUTYAW;

void pid_equation( float Error, float P, float I, float D, float PrevError, float PrevIterm, float Imax, float Umax){

  float Pterm = P*Error;

  float Iterm = PrevIterm + I*Error*0.005;
  if(Iterm > Imax) {
    Iterm = Imax;
  } else if (Iterm < -Imax ) {
    Iterm = -Imax;
  }

  float Dterm = D*(Error-PrevError)/0.005;

  float PID = Pterm + Iterm + Dterm;
  if( PID > Umax) {
    PID = Umax;
  } else if( PID < -Umax){
    PID = -Umax;
  }

  PIDOutput[0] = PID;
  PIDOutput[1] = Error;
  PIDOutput[2] = Iterm;

}

void reset_pid(){ // xã đầy tích phân
  PreItermAngleRoll*=0.9; 
  PreItermAnglePitch*=0.9;
  PreItermAngleYaw*=0.9;

  PreItermRateRoll*=0.9; 
  PreItermRatePitch*=0.9;
  PreItermRateYaw*=0.9;
}

void reset_status_flight() {  // sử dụng khi disarm
  PreItermAngleRoll=0; 
  PreItermAnglePitch=0;
  PreItermAngleYaw=0;

  PreItermRateRoll=0; 
  PreItermRatePitch=0;
  PreItermRateYaw=0; 
  
}

void PID_Angle(float Roll_target, float Pitch_target, float Yaw_target, float Roll, float Pitch, float Yaw ) {

  ErrorAngleRoll = Roll_target - Roll;

  pid_equation( ErrorAngleRoll, PAngleRoll, IAngleRoll, DAngleRoll, PreErrorAngleRoll, PreItermAngleRoll, 50, 400 );
  Desired_RateRoll = PIDOutput[0];
  PreErrorAngleRoll = PIDOutput[1];
  PreItermAngleRoll = PIDOutput[2];

  ErrorAnglePitch = Pitch_target - Pitch;

  pid_equation( ErrorAnglePitch, PAnglePitch, IAnglePitch, DAnglePitch, PreErrorAnglePitch, PreItermAnglePitch, 50, 400 );
  Desired_RatePitch = PIDOutput[0];
  PreErrorAnglePitch = PIDOutput[1];
  PreItermAnglePitch = PIDOutput[2];
  
  //ErrorAngleYaw = Yaw_target - Yaw;

  // pid_equation( ErrorAngleYaw, PAngleYaw, IAngleYaw, DAngleYaw, PreErrorAngleYaw, PreItermAngleYaw, 0, 90 );
  // Desired_RateYaw = PIDOutput[0];
  // PreErrorAngleYaw = PIDOutput[1];
  // PreItermAngleYaw = PIDOutput[2];
}

void PID_Rate( float RateRoll_target , float RatePitch_target , float RateYaw_target, float RATERoll , float RATEPitch , float RATEYaw ) {

  ErrorRateRoll = RateRoll_target - RATERoll;
  pid_equation( ErrorRateRoll, PRateRoll, IRateRoll, DRateRoll, PreErrorRateRoll, PreItermRateRoll, 200, 400 );
  INPUTROLL = PIDOutput[0];
  PreErrorRateRoll = PIDOutput[1];
  PreItermRateRoll = PIDOutput[2];
  
  ErrorRatePitch = RatePitch_target - RATEPitch;
  pid_equation( ErrorRatePitch, PRatePitch, IRatePitch, DRatePitch, PreErrorRatePitch, PreItermRatePitch, 200, 400 );
  INPUTPITCH = PIDOutput[0];
  PreErrorRatePitch = PIDOutput[1];
  PreItermRatePitch = PIDOutput[2];

  ErrorRateYaw = RateYaw_target - RATEYaw;
  pid_equation( ErrorRateYaw, PRateYaw, IRateYaw, DRateYaw, PreErrorRateYaw, PreItermRateYaw, 100, 200 );
  INPUTYAW = PIDOutput[0];
  PreErrorRateYaw = PIDOutput[1];
  PreItermRateYaw = PIDOutput[2];

}

















