class Console:
    class Colors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKCYAN = '\033[96m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

    @staticmethod
    def err(s: str):
        print(f"{Console.Colors.FAIL}{s}{Console.Colors.ENDC}")

    @staticmethod
    def ok(s: str):
        print(f"{Console.Colors.OKGREEN}{s}{Console.Colors.ENDC}")

    @staticmethod
    def warn(s: str):
        print(f"{Console.Colors.WARNING}{s}{Console.Colors.ENDC}")

    @staticmethod
    def info(s: str):
        print(s)
