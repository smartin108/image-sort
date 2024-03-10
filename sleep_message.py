class sleep_message:
    """feature req lol : option with twirly, even better with slick decay profiles"""

    def __init__(self, **args):
        message = args.get('message')
        if args.get('sleep_time'):
            sleep_time = args.get('sleep_time')
        else:
            sleep_time = float(5.0)

        if args.get('trailing_spaces'):
            trailing_spaces = args.get('trailing_spaces')
        else:
            trailing_spaces = 5

        if args.get('time_increment'):
            time_increment = args.get('time_increment')
        else:
            time_increment = 0.1


        """display a countdown timer while sleeping"""
        if sleep_time < 0.5:
            sleep(sleep_time)
        else:
            countdown = floor(sleep_time)
            while countdown > -1e-10:
                regular_message = message.replace('%', str(int(countdown)))
                stdout.write(f'\r{regular_message}{" "*trailing_spaces}')
                stdout.flush()
                sleep(time_increment)
                countdown -= time_increment
            print('\n')
        return 1
