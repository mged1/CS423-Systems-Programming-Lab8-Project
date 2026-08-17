OPTAB = {
    "LDA": "00",
    "ADD": "18",
    "STA": "0C",
    "JSUB": "48"
}

MEMORY_SIZE = 0x4000


def parse_line(line):
    parts = line.split()

    if len(parts) == 3:
        return parts[0], parts[1], parts[2]

    if len(parts) == 2:
        return "", parts[0], parts[1]

    if len(parts) == 1:
        return "", parts[0], ""

    return "", "", ""


def byte_length(operand):
    if operand.startswith("C'") and operand.endswith("'"):
        return len(operand[2:-1])

    if operand.startswith("X'") and operand.endswith("'"):
        return len(operand[2:-1]) // 2

    return 1


def instruction_size(opcode):
    if opcode.startswith("+"):
        return 4

    return 3


def pass_one(filename):
    symtab = {}
    records = []
    locctr = 0
    start_address = 0
    execution_address = 0

    with open(filename, "r") as file:
        lines = file.readlines()

    for line in lines:
        line = line.strip()

        if not line:
            continue

        label, opcode, operand = parse_line(line)
        opcode_upper = opcode.upper()

        if opcode_upper == "START":
            start_address = int(operand, 16)
            locctr = start_address
            execution_address = start_address

            if label:
                symtab[label] = locctr

            records.append((locctr, label, opcode, operand))
            continue

        if label:
            if label in symtab:
                print(f"ERROR: Duplicate symbol {label}")
            else:
                symtab[label] = locctr

        records.append((locctr, label, opcode, operand))

        if opcode_upper == "END":
            break
        elif opcode_upper == "WORD":
            locctr += 3
        elif opcode_upper == "BYTE":
            locctr += byte_length(operand)
        elif opcode_upper == "RESW":
            locctr += int(operand) * 3
        elif opcode_upper == "RESB":
            locctr += int(operand)
        elif opcode_upper in OPTAB or opcode_upper.startswith("+"):
            locctr += instruction_size(opcode_upper)

    program_length = locctr - start_address

    return records, symtab, start_address, program_length, execution_address


def get_operand_value(operand, symtab):
    if operand.startswith("#") or operand.startswith("@"):
        operand = operand[1:]

    if operand.endswith(",X"):
        operand = operand[:-2]

    if operand.isdigit():
        return int(operand)

    return symtab.get(operand)


def make_object_code(opcode, operand, address, symtab):
    if opcode.upper() in ["START", "END", "RESW", "RESB"]:
        return ""

    if opcode.upper() == "WORD":
        return f"{int(operand):06X}"

    if opcode.upper() == "BYTE":
        if operand.startswith("C'") and operand.endswith("'"):
            text = operand[2:-1]
            result = ""

            for character in text:
                result += f"{ord(character):02X}"

            return result

        if operand.startswith("X'") and operand.endswith("'"):
            return operand[2:-1].upper()

    extended = opcode.startswith("+")
    clean_opcode = opcode[1:] if extended else opcode
    base_opcode = int(OPTAB[clean_opcode.upper()], 16)

    n = 1
    i = 1

    if operand.startswith("#"):
        n = 0
        i = 1
    elif operand.startswith("@"):
        n = 1
        i = 0

    x = 0
    clean_operand = operand

    if clean_operand.startswith("#") or clean_operand.startswith("@"):
        clean_operand = clean_operand[1:]

    if clean_operand.endswith(",X"):
        x = 1
        clean_operand = clean_operand[:-2]

    target = get_operand_value(operand, symtab)

    if target is None:
        print(f"ERROR: Undefined symbol {clean_operand}")
        return ""

    first_byte = (base_opcode & 0xFC) + (n * 2) + i

    if extended:
        flags = (x << 3) + 1
        value = (first_byte << 24) + (flags << 20) + target
        return f"{value:08X}"

    if operand.startswith("#") and clean_operand.isdigit():
        displacement = target
        b = 0
        p = 0
    else:
        pc = address + 3
        displacement = target - pc

        if -2048 <= displacement <= 2047:
            b = 0
            p = 1
        else:
            b = 0
            p = 0
            displacement = target

    displacement = displacement & 0xFFF
    flags = (x << 3) + (b << 2) + (p << 1)

    value = (first_byte << 16) + (flags << 12) + displacement

    return f"{value:06X}"


def pass_two(records, symtab, start_address, program_length, execution_address):
    object_codes = []

    print()
    print("ASSEMBLY LISTING")
    print("Address  Label    Opcode   Operand      Object Code")
    print("-" * 58)

    for address, label, opcode, operand in records:
        code = make_object_code(opcode, operand, address, symtab)
        object_codes.append((address, code))

        print(f"{address:06X}   {label:<8} {opcode:<8} {operand:<12} {code}")

    create_object_file(
        object_codes,
        start_address,
        program_length,
        execution_address
    )

    return object_codes


def create_text_records(object_codes):
    text_records = []
    start = None
    code = ""
    byte_count = 0

    for address, object_code in object_codes:
        if object_code == "":
            if code:
                text_records.append(
                    f"T{start:06X}{byte_count:02X}{code}"
                )
                start = None
                code = ""
                byte_count = 0

            continue

        object_bytes = len(object_code) // 2

        if start is None:
            start = address

        if byte_count + object_bytes > 30:
            text_records.append(
                f"T{start:06X}{byte_count:02X}{code}"
            )

            start = address
            code = ""
            byte_count = 0

        code += object_code
        byte_count += object_bytes

    if code:
        text_records.append(
            f"T{start:06X}{byte_count:02X}{code}"
        )

    return text_records


def create_object_file(object_codes, start_address, program_length,
                       execution_address):
    header = f"H{'DEMO':<6}{start_address:06X}{program_length:06X}"
    text_records = create_text_records(object_codes)
    end = f"E{execution_address:06X}"

    with open("program.obj", "w") as file:
        file.write(header + "\n")

        for record in text_records:
            file.write(record + "\n")

        file.write(end + "\n")


def load_object_file(filename):
    memory = ["XX"] * MEMORY_SIZE
    execution_address = 0

    with open(filename, "r") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            if line.startswith("H"):
                print()
                print(f"Header: {line}")

            elif line.startswith("T"):
                start_address = int(line[1:7], 16)
                object_code = line[9:]

                for position in range(0, len(object_code), 2):
                    byte_value = object_code[position:position + 2]
                    memory[start_address] = byte_value
                    start_address += 1

                print(f"Loaded text record: {line}")

            elif line.startswith("E"):
                execution_address = int(line[1:7], 16)
                print(f"Execution starts at: {execution_address:06X}")

    return memory, execution_address


def display_memory(memory, start_address, end_address):
    print()
    print("MEMORY DUMP")
    print("Address    " + " ".join(f"{x:02X}" for x in range(16)))
    print("-" * 76)

    address = start_address

    while address <= end_address:
        values = memory[address:address + 16]
        print(f"{address:06X}    " + " ".join(values))
        address += 16


def main():
    records, symtab, start_address, program_length, execution_address = \
        pass_one("fresh_program.txt")

    print("SYMBOL TABLE")
    for name, address in symtab.items():
        print(f"{name:<10} {address:04X}")

    object_codes = pass_two(
        records,
        symtab,
        start_address,
        program_length,
        execution_address
    )

    memory, execution_address = load_object_file("program.obj")

    print()
    print(f"Program length: {program_length:06X}")
    print(f"Execution address: {execution_address:06X}")

    display_memory(memory, start_address, start_address + 0x30)


if __name__ == "__main__":
    main()