import time

sleep = 1

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
                display_menu()
                continue

            elif opt == 1:
                phase = amp.phase()
                print(f"Phase: {phase} degrees")
                time.sleep(sleep)

            elif opt == 2:
                phase = amp.set_phase()

                print(f"Phase set to: {phase} degrees")
                time.sleep(sleep)

        # Reference Source
        elif nav == 2:
            opt = function_options("Reference Source")

            if opt == 0:
                display_menu()
                continue

            elif opt == 1:
                ref_source = amp.reference_source()
                print(f"Reference source: {ref_source}")
                time.sleep(sleep)

            elif opt == 2:
                ref_source = amp.set_reference_source()
                print(f"Reference source set to: {ref_source}")
                time.sleep(sleep)


        elif nav == 3:
            opt = function_options("Frequency")
            if opt == 0:
                continue
            elif opt == 1:
                amp.frequency()
            elif opt == 2:
                amp.set_frequency()


        elif nav == 4:
            opt = function_options("Reference Trigger")


        elif nav == 5:
            opt = function_options("Detection Harmonic")

        
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
