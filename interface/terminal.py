import time
import logging

logger = logging.getLogger(__name__)

PAUSE = 1

functions = {
    "REFERENCE and PHASE COMMANDS": ["phase", "reference source", "frequency", "reference trigger", "detection harmonic", "sine amplitude"],
    "INPUT and FILTER COMMANDS": ["input configuration", "input shield grounding", "input coupling", "input line notch filter status"],
    "GAIN and TIME CONSTANT COMMANDS": ["sensitivity", "reserve mode", "time constant", "low pass filter slope", "synchronous filter status"]
}


def display_menu():
    print("\n" + "=" * 40)
    print("   Lock-in Amplifier Control")
    print("=" * 40)

    item_count = 0
    print(f"  {item_count}. Exit")

    for category, setting in functions.items():
        print(f"{category}")


        for function in setting:
            item_count += 1
            print(f"  {item_count}. {function.title()}")

    return item_count


def function_options(func):
    print(f"\n{func}")
    print("-" * 30)
    print("  0. Back")
    print(f"  1. Get {func}")
    print(f"  2. Set {func}")

    choice = None
    options = [0, 1, 2]
    while choice not in options:
        try:
            choice = int(input("> "))

        except ValueError:
            print("Input a valid number in the range 0-2\n")

    return choice



def simulation(amp):
    item_count = display_menu()

    while True:
        
        try:
            nav = int(input("> "))

        except ValueError:
            print(f"Input a valid number in the range 0-{item_count}\n")
            continue

        if nav not in range(0, item_count + 1):
            print(f"Input a valid number in the range 0-{item_count}\n")


        if nav == 0:
            print("Exiting...")
            break


        # Phase shift
        elif nav == 1:
            opt = function_options("Phase")
 
            if opt == 0:
                pass
 
            elif opt == 1:
                phase = amp.phase()
                print(f"\n  Phase: {phase} degrees")
                logger.info("Read phase: %.2f degrees", phase)
                time.sleep(PAUSE)
 
            elif opt == 2:
                print("  Range: -360 to +729.99 degrees")
                try:
                    phase = float(input("  Enter phase (degrees): "))

                except ValueError:
                    print("  Invalid input — must be a number.")
                    display_menu()
                    continue
                try:
                    amp.set_phase(phase)
                    print(f"  Phase set to: {phase} degrees")

                except ValueError as e:
                    print(f"  Error: {e}")
                time.sleep(PAUSE)


        # Reference Source
        elif nav == 2:
            opt = function_options("Reference Source")
 
            if opt == 0:
                pass
 
            elif opt == 1:
                src = amp.reference_source()
                label = "Internal" if src == 1 else "External"
                print(f"\n  Reference source: {src} ({label})")
                logger.info(f"Read reference source: {src} ({label})")
                time.sleep(PAUSE)
 
            elif opt == 2:
                print("  0 = External  |  1 = Internal")

                try:
                    i = int(input("  Enter reference source (0 or 1): "))

                except ValueError:
                    print("  Invalid input — must be 0 or 1.")
                    display_menu()
                    continue

                try:
                    amp.set_reference_source(i)
                    label = "Internal" if i == 1 else "External"
                    print(f"  Reference source set to: {i} ({label})")

                except ValueError as e:
                    print(f"  Error: {e}")

                time.sleep(PAUSE)


        # Freuency
        elif nav == 3:
            opt = function_options("Frequency")
 
            if opt == 0:
                pass
 
            elif opt == 1:
                freq = amp.frequency()
                print(f"\n  Frequency: {freq} Hz")
                logger.info(f"Read frequency: {freq:.4f} Hz")
                time.sleep(PAUSE)
 
            elif opt == 2:
                print("  Range: 0.001 to 102,000 Hz")
                try:
                    freq = float(input("  Enter frequency (Hz): "))

                except ValueError:
                    print("  Invalid input — must be a number.")
                    display_menu()
                    continue

                try:
                    amp.set_frequency(freq)
                    print(f"  Frequency set to: {freq} Hz")

                except ValueError as e:
                    print(f"  Error: {e}")

                time.sleep(PAUSE)

        # Reference Trigger
        elif nav == 4:
            opt = function_options("Reference Trigger")
 
            if opt == 0:
                pass
 
            elif opt == 1:
                trig = amp.reference_trigger()
                labels = {0: "Sine zero crossing", 1: "TTL rising edge", 2: "TTL falling edge"}
                print(f"\n  Reference trigger: {trig} ({labels.get(trig, '?')})")
                time.sleep(PAUSE)
 
            elif opt == 2:
                print("  0 = Sine zero crossing  |  1 = TTL rising  |  2 = TTL falling")

                try:
                    i = int(input("  Enter trigger mode (0, 1, or 2): "))

                except ValueError:
                    print("  Invalid input — must be 0, 1, or 2.")
                    display_menu()
                    continue

                try:
                    amp.set_reference_trigger(i)
                    print(f"  Reference trigger set to: {i}")

                except ValueError as e:
                    print(f"  Error: {e}")

                time.sleep(PAUSE)
 
        # Detection Harmonic
        elif nav == 5:
            opt = function_options("Detection Harmonic")
 
            if opt == 0:
                pass
 
            elif opt == 1:
                h = amp.detection_harmonic()
                print(f"\n  Detection harmonic: {h}")
                time.sleep(PAUSE)
 
            elif opt == 2:
                print("  Range: 1 to 19999 (note: i x frequency must not exceed 102 kHz)")

                try:
                    i = int(input("  Enter harmonic number: "))

                except ValueError:
                    print("  Invalid input — must be a whole number.")
                    display_menu()
                    continue

                try:
                    amp.set_detection_harmonic(i)
                    print(f"  Detection harmonic set to: {i}")

                except ValueError as e:
                    print(f"  Error: {e}")

                time.sleep(PAUSE)
        

        elif nav == 6:
            opt = function_options("Sine Amplitude")


        elif nav == 7:
            opt = function_options("Input Configuration")

        elif nav == 8:
            opt = function_options("Input Shield Grounding")
        
        elif nav == 9:
            opt = function_options("Input Coupling")
        
        elif nav == 10:
            opt = function_options("Input Line Notch Filter")

        elif nav == 11:
            opt = function_options("Sensitivity")
        
        elif nav == 12:
            opt = function_options("Reserve Mode")
        
        elif nav == 13:
            opt = function_options("Time Constant")
        
        elif nav == 14:
            opt = function_options("Low Pass Filter Slope")
        
        elif nav == 15:
            opt = function_options("Synchronous Filter")

        
        display_menu()
