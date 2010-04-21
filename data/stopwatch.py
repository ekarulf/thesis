import curses
import os.path
import sys
from time import time

QUIT = ord('q')

def main(stdscr, filename):
    times = [time()]
    try:
        while True:
            # Display
            stdscr.addstr(0, 0, "%d times recorded" % (len(times) - 1))
            stdscr.refresh()
            # Process User Input
            key = stdscr.getch()
            if key == QUIT:
                break
            else:
                times.append(time())
    except KeyboardInterrupt:
        pass
    
    # Save to disk
    directory = os.path.dirname(filename)
    filename  = os.path.basename(filename) + ".txt"
    f = open(os.path.join(directory, filename), 'w')
    f.write('\n'.join([str(t) for t in times]))
    f.close()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        curses.wrapper(main, filename)
    else:
        print "usage: %s filename" % sys.argv[0]
