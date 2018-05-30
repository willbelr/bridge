#!/usr/bin/python3
import argparse
import dbus
import sys

try:
    import bridge.main as bridge
except ImportError:
    import main as bridge


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-o", "--open", help="open a file with the monitor", metavar='')
    group.add_argument("-u", "--upload", help="upload firmware from a file", metavar='')
    group.add_argument("-s", "--send", nargs="+", help="send data through the active serial connection", metavar='')
    args = parser.parse_args()

    if args.upload:
        slave = bridge.Slave()
        slave.execute(args.upload, upload=True)
        slave.waitForFinished(-1)
        sys.exit(0)

    if args.open:
        # Create a custom profile instance
        bridge.main(args.open)
    else:
        # Open as standalone
        try:
            # Verify if the bus already exist
            bus = dbus.SessionBus()
            session = bus.get_object("org.bridge.session", "/org/bridge/session")
            interface = dbus.Interface(session, "org.bridge.session")

            # Handle command line input
            if args.send:
                for arg in args.send:
                    interface.send(arg)
            sys.exit(0)

        except dbus.exceptions.DBusException:
            # Create a new standalone instance
            bridge.main()


if __name__ == '__main__':
    main()
