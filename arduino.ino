#include <Servo.h>

Servo myServo;

const int trigPin = 7;
const int echoPin = 6;
const int buzzerPin = 2;
const int ledPin = 3;

long duration;
int distance;


bool buzzerEnabled = false;

void setup() {
  Serial.begin(9600);
  myServo.attach(9);
  myServo.write(10);  // initial position

  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(buzzerPin, OUTPUT);
  pinMode(ledPin, OUTPUT);
}

void loop() {
  // Continuously measure and print distance
  distance = getDistance();

  Serial.print("Distance: ");
  Serial.print(distance);
  Serial.println(" cm");

  if (buzzerEnabled) {
    if (distance > 0 && distance < 10) {
      digitalWrite(buzzerPin, HIGH);
      digitalWrite(ledPin, HIGH);    // turn LED on
    } else {
      digitalWrite(buzzerPin, LOW);
      digitalWrite(ledPin, LOW);     // turn LED off
    }
  } else {
    digitalWrite(buzzerPin, LOW); // always off when disabled
    digitalWrite(ledPin, LOW);       // LED off
  }

  delay(200);  // adjust delay as needed
}

// Called automatically when serial data arrives
void serialEvent() {
  while (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim(); // remove trailing newline and whitespace

    // Control servo
    if (input.toInt() >= 10 && input.toInt() <= 170) {
      int pos = input.toInt();
      myServo.write(pos);
      Serial.print("Moved to: ");
      Serial.println(pos);
    }

    // Control buzzer
    else if (input == "TURN_BUZZER_ON") {
      buzzerEnabled = true;
      Serial.println("Buzzer Enabled");
    } else if (input == "TURN_BUZZER_OFF") {
      buzzerEnabled = false;
      digitalWrite(buzzerPin, LOW); // immediately turn off
      Serial.println("Buzzer Disabled");
    }
  }
}

int getDistance() {
  // Trigger ultrasonic sensor
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Read the echo pulse duration
  duration = pulseIn(echoPin, HIGH);

  // Calculate distance in cm
  distance = duration * 0.034 / 2;

  return distance;
}
