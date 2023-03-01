#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>


static volatile sig_atomic_t run_forever;


static void sig_handler(int signum){
	(void) signum;

	run_forever = 0;
}

void print_help()
{
	printf("Helper application for testing of executable module.\n");
	printf("\n");
	printf("The application produces requested output on stdout and/or stderr. It can\n"
			"run forever (until it is terminated using SIGINT or SIGTERM) and based on \n"
			"arguments it finishes successfully or dies with segfault.\n");
	printf("\n");
	printf("Options:\n");
	printf("-h   Print this help and exit.\n");
	printf("-d sec   Exit after 'sec' delay. Cannot be used with '-f'.\n");
	printf("-f sec   Run forever. Print requested message on stdout and/or stderr every 'sec' seconds. Cannot be used with '-d'.\n");
	printf("-s   Die on segfault. Print requested message on stdout ('-o') and/or stderr ('-e') once first.\n");
	printf("-o msg   Print message 'msg' on stdout (every 'sec' seconds when '-f' is used).\n");
	printf("-e msg   Print message 'msg' on stderr (every 'sec' seconds when '-f' is used).\n");
	printf("-r code   Exit with return code 'code'.\n");
	printf("\n");
	printf("Examples:\n");
	printf("\n");
	printf("Do nothing:\n");
	printf("./helper_app\n");
	printf("\n");
	printf("Print nothing and die with segfault:\n");
	printf("./helper_app -s\n");
	printf("\n");
	printf("Print 'funny out' to stdout and 'more funny err' to stderr every 2 seconds: unless\n"
			"SIGINT or SIGTERM is sent.\n");
	printf("./helper_app -f -o 'funny out' -e 'more funny err'\n");
}

void print_outputs(char *print_stdout, char *print_stderr)
{
	if (print_stdout)
		printf("%s", print_stdout);

	if (print_stderr)
		fprintf(stderr, "%s", print_stderr);

	fflush(stdout);
	fflush(stderr);
}

int main(int argc, char *argv[]) {
	char *ptr = NULL;
	int do_segfault = 0;
	char *print_stdout = NULL;
	char *print_stderr = NULL;
	int c;
	int exit_delay;
	int ret_code = 0;

	signal(SIGINT, sig_handler);
	signal(SIGTERM, sig_handler);

	run_forever = 0;
	exit_delay = 0;

	while ((c = getopt(argc, argv, "hd:f:so:e:r:")) != -1) {
		switch (c){
		case 'h':
			print_help();
			return 0;
			break;
		case 'd':
			exit_delay = atoi(optarg);
			break;
		case 'f':
			run_forever = atoi(optarg);
			break;
		case 's':
			do_segfault = 1;
			break;
		case 'o':
			print_stdout = optarg;
			break;
		case 'e':
			print_stderr = optarg;
			break;
		case 'r':
			ret_code = atoi(optarg); // this will be overriden on unknown argument
			break;
		default:
			ret_code = 1;
			break;
		}
	}

	if (run_forever > 0 && exit_delay > 0) {
		fprintf(stderr, "Invalid arguments: '-d' and '-f' used together.\n");
		exit(1);
	}

	do {
		print_outputs(print_stdout, print_stderr);

		if (do_segfault)
			*ptr = 'a';

		sleep(run_forever);
	} while(run_forever);

	sleep(exit_delay);

	return ret_code;
}
