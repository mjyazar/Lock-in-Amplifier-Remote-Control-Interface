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
                print("  0 = Sine zero crossing\n  1 = TTL rising edge\n  2 = TTL falling edge")

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
        
        # Sine Amplitude
        elif nav == 6:
            opt = function_options("Sine Amplitude")
 
            if opt == 0:
                pass
 
            elif opt == 1:
                amp_val = amp.sine_amplitude()
                print(f"\n  Sine amplitude: {amp_val} Vrms")
                logger.info(f"Read sine amplitude: {amp_val:.3f} Vrms")
                time.sleep(PAUSE)
 
            elif opt == 2:
                print("  Range: 0.004 to 5.000 Vrms")

                try:
                    x = float(input("  Enter amplitude (Vrms): "))

                except ValueError:
                    print("  Invalid input — must be a number.")
                    display_menu()
                    continue

                try:
                    amp.set_sine_amplitude(x)
                    print(f"  Sine amplitude set to: {x} Vrms")
                    logger.info(f"Set sine amplitude: {x:.3f} Vrms")

                except ValueError as e:
                    print(f"  Error: {e}")
                    logger.error(f"Failed to set sine amplitude: {e}")
                time.sleep(PAUSE)
 
        # Input Configuration
        elif nav == 7:
            opt = function_options("Input Configuration")

            if opt == 0:
                pass

            elif opt == 1:
                i = amp.input_configuration()
                labels = {0: "A", 1: "A-B", 2: "I (1 MΩ)", 3: "I (100 MΩ)"}
                print(f"\n  Input configuration: {i} ({labels.get(i, '?')})")
                time.sleep(PAUSE)

            elif opt == 2:
                print("  0 = A\n  1 = A-B\n  2 = I (1 MΩ)\n  3 = I (100 MΩ)")
                try:
                    i = int(input("  Enter input configuration (0-3): "))
                except ValueError:
                    print("  Invalid input — must be 0, 1, 2, or 3.")
                    display_menu()
                    continue
                try:
                    amp.set_input_configuration(i)
                    labels = {0: "A", 1: "A-B", 2: "I (1 MΩ)", 3: "I (100 MΩ)"}
                    print(f"  Input configuration set to: {i} ({labels[i]})")
                except ValueError as e:
                    print(f"  Error: {e}")
                time.sleep(PAUSE)

        # Input Shield Grounding
        elif nav == 8:
            opt = function_options("Input Shield Grounding")

            if opt == 0:
                pass

            elif opt == 1:
                i = amp.input_shield_grounding()
                labels = {0: "Float", 1: "Ground"}
                print(f"\n  Input shield grounding: {i} ({labels.get(i, '?')})")
                time.sleep(PAUSE)

            elif opt == 2:
                print("  0 = Float\n  1 = Ground")
                try:
                    i = int(input("  Enter shield grounding (0 or 1): "))
                except ValueError:
                    print("  Invalid input — must be 0 or 1.")
                    display_menu()
                    continue
                try:
                    amp.set_input_shield_grounding(i)
                    labels = {0: "Float", 1: "Ground"}
                    print(f"  Shield grounding set to: {i} ({labels[i]})")
                except ValueError as e:
                    print(f"  Error: {e}")
                time.sleep(PAUSE)

        # Input Coupling
        elif nav == 9:
            opt = function_options("Input Coupling")

            if opt == 0:
                pass

            elif opt == 1:
                i = amp.input_coupling()
                labels = {0: "AC", 1: "DC"}
                print(f"\n  Input coupling: {i} ({labels.get(i, '?')})")
                time.sleep(PAUSE)

            elif opt == 2:
                print("  0 = AC\n  1 = DC")
                try:
                    i = int(input("  Enter input coupling (0 or 1): "))
                except ValueError:
                    print("  Invalid input — must be 0 or 1.")
                    display_menu()
                    continue
                try:
                    amp.set_input_coupling(i)
                    labels = {0: "AC", 1: "DC"}
                    print(f"  Input coupling set to: {i} ({labels[i]})")
                except ValueError as e:
                    print(f"  Error: {e}")
                time.sleep(PAUSE)

        # Input Line Notch Filter Status
        elif nav == 10:
            opt = function_options("Input Line Notch Filter")

            if opt == 0:
                pass

            elif opt == 1:
                i = amp.input_line_notch_filter()
                labels = {0: "No filters", 1: "Line notch", 2: "2× Line notch", 3: "Both filters"}
                print(f"\n  Input line notch filter: {i} ({labels.get(i, '?')})")
                time.sleep(PAUSE)

            elif opt == 2:
                print("  0 = No filters\n  1 = Line notch\n  2 = 2× Line notch\n  3 = Both filters")
                try:
                    i = int(input("  Enter notch filter setting (0-3): "))
                except ValueError:
                    print("  Invalid input — must be 0, 1, 2, or 3.")
                    display_menu()
                    continue
                try:
                    amp.set_input_line_notch_filter(i)
                    labels = {0: "No filters", 1: "Line notch", 2: "2× Line notch", 3: "Both filters"}
                    print(f"  Notch filter set to: {i} ({labels[i]})")
                except ValueError as e:
                    print(f"  Error: {e}")
                time.sleep(PAUSE)

        # Sensitivity
        elif nav == 11:
            opt = function_options("Sensitivity")

            if opt == 0:
                pass

            elif opt == 1:
                i = amp.sensitivity()
                from amplifier.sr830 import SR830
                label = SR830.SENSITIVITY.get(i, ['?'])[0]
                print(f"\n  Sensitivity: {i} ({label})")
                time.sleep(PAUSE)

            elif opt == 2:
                from amplifier.sr830 import SR830
                print("  Sensitivity index → value:")
                for k, v in SR830.SENSITIVITY.items():
                    print(f"    {k:2d} = {v[0]}")
                try:
                    i = int(input("  Enter sensitivity index (0-26): "))
                except ValueError:
                    print("  Invalid input — must be a whole number.")
                    display_menu()
                    continue
                try:
                    amp.set_sensitivity(i)
                    print(f"  Sensitivity set to: {i} ({SR830.SENSITIVITY[i][0]})")
                except ValueError as e:
                    print(f"  Error: {e}")
                time.sleep(PAUSE)

        # Reserve Mode
        elif nav == 12:
            opt = function_options("Reserve Mode")

            if opt == 0:
                pass

            elif opt == 1:
                i = amp.reserve_mode()
                labels = {0: "High Reserve", 1: "Normal", 2: "Low Noise"}
                print(f"\n  Reserve mode: {i} ({labels.get(i, '?')})")
                time.sleep(PAUSE)

            elif opt == 2:
                print("  0 = High Reserve\n  1 = Normal\n  2 = Low Noise")
                try:
                    i = int(input("  Enter reserve mode (0, 1, or 2): "))
                except ValueError:
                    print("  Invalid input — must be 0, 1, or 2.")
                    display_menu()
                    continue
                try:
                    amp.set_reserve_mode(i)
                    labels = {0: "High Reserve", 1: "Normal", 2: "Low Noise"}
                    print(f"  Reserve mode set to: {i} ({labels[i]})")
                except ValueError as e:
                    print(f"  Error: {e}")
                time.sleep(PAUSE)

        # Time Constant
        elif nav == 13:
            opt = function_options("Time Constant")

            if opt == 0:
                pass

            elif opt == 1:
                i = amp.time_constant()
                from amplifier.sr830 import SR830
                label = SR830.TIME_CONSTANT.get(i, ['?'])[0]
                print(f"\n  Time constant: {i} ({label})")
                time.sleep(PAUSE)

            elif opt == 2:
                from amplifier.sr830 import SR830
                print("  Time constant index → value:")
                for k, v in SR830.TIME_CONSTANT.items():
                    print(f"    {k:2d} = {v[0]}")
                try:
                    i = int(input("  Enter time constant index (0-19): "))
                except ValueError:
                    print("  Invalid input — must be a whole number.")
                    display_menu()
                    continue
                try:
                    amp.set_time_constant(i)
                    print(f"  Time constant set to: {i} ({SR830.TIME_CONSTANT[i][0]})")
                except ValueError as e:
                    print(f"  Error: {e}")
                time.sleep(PAUSE)

        # Low Pass Filter Slope
        elif nav == 14:
            opt = function_options("Low Pass Filter Slope")

            if opt == 0:
                pass

            elif opt == 1:
                i = amp.low_pass_filter_slope()
                labels = {0: "6 dB/oct", 1: "12 dB/oct", 2: "18 dB/oct", 3: "24 dB/oct"}
                print(f"\n  Low pass filter slope: {i} ({labels.get(i, '?')})")
                time.sleep(PAUSE)

            elif opt == 2:
                print("  0 = 6 dB/oct\n  1 = 12 dB/oct\n  2 = 18 dB/oct\n  3 = 24 dB/oct")
                try:
                    i = int(input("  Enter filter slope (0-3): "))
                except ValueError:
                    print("  Invalid input — must be 0, 1, 2, or 3.")
                    display_menu()
                    continue
                try:
                    amp.set_low_pass_filter_slope(i)
                    labels = {0: "6 dB/oct", 1: "12 dB/oct", 2: "18 dB/oct", 3: "24 dB/oct"}
                    print(f"  Filter slope set to: {i} ({labels[i]})")
                except ValueError as e:
                    print(f"  Error: {e}")
                time.sleep(PAUSE)

        # Synchronous Filter
        elif nav == 15:
            opt = function_options("Synchronous Filter")

            if opt == 0:
                pass

            elif opt == 1:
                i = amp.synchronous_filter()
                labels = {0: "Off", 1: "On (< 200 Hz)"}
                print(f"\n  Synchronous filter: {i} ({labels.get(i, '?')})")
                time.sleep(PAUSE)

            elif opt == 2:
                print("  0 = Off\n  1 = On (synchronous filtering below 200 Hz)")
                try:
                    i = int(input("  Enter synchronous filter (0 or 1): "))
                except ValueError:
                    print("  Invalid input — must be 0 or 1.")
                    display_menu()
                    continue
                try:
                    amp.set_synchronous_filter(i)
                    labels = {0: "Off", 1: "On (< 200 Hz)"}
                    print(f"  Synchronous filter set to: {i} ({labels[i]})")
                except ValueError as e:
                    print(f"  Error: {e}")
                time.sleep(PAUSE)

        display_menu()
