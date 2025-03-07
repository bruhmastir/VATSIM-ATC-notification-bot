from datetime import datetime

log_file = "log to check.log"

def extract_timestamp(line):
    """Extracts timestamp from log line."""
    return datetime.strptime(line.split(" - ")[0], "%Y-%m-%d %H:%M:%S,%f")

def get_first_and_last_timestamp(log_file):
    """Gets timestamps of first and last lines in a log file."""
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        if not lines:
            print("Log file is empty.")
            return None, None

        first_timestamp = extract_timestamp(lines[0])
        last_timestamp = extract_timestamp(lines[-1])

        return first_timestamp, last_timestamp

# Get timestamps
first_time, last_time = get_first_and_last_timestamp(log_file)

if first_time and last_time:
    time_diff = last_time - first_time
    print(f"Start Time: {first_time}")
    print(f"End Time: {last_time}")
    print(f"Duration: {time_diff}")








log_file = "log to check.log"

def extract_timestamp(line):
    """Extracts timestamp from log line."""
    return datetime.strptime(line.split(" - ")[0], "%Y-%m-%d %H:%M:%S,%f")

def find_max_time_difference_consecutive(log_file):
    """Finds the two consecutive lines with the largest time difference."""
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        if len(lines) < 2:
            print("Not enough data in log file.")
            return None, None, None

        max_diff = None
        max_pair = None

        prev_time = extract_timestamp(lines[0])
        prev_line = lines[0].strip()

        for i in range(1, len(lines)):
            curr_time = extract_timestamp(lines[i])
            curr_line = lines[i].strip()

            time_diff = curr_time - prev_time  # Difference between consecutive lines

            if max_diff is None or time_diff > max_diff:
                max_diff = time_diff
                max_pair = (prev_line, curr_line)

            prev_time = curr_time
            prev_line = curr_line

        return max_pair, max_diff

# Run function
(max_line1, max_line2), max_time_diff = find_max_time_difference_consecutive(log_file)

if max_line1 and max_line2:
    print(f"Line 1: {max_line1}")
    print(f"Line 2: {max_line2}")
    print(f"Maximum Time Difference: {max_time_diff}")
