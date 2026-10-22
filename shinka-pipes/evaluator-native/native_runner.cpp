// The original official checker runs here; only its I/O transport is adapted.
#include "testlib.h"
#include <atomic>
#include <chrono>
#include <cerrno>
#include <csignal>
#include <cstring>
#include <fcntl.h>
#include <poll.h>
#include <sys/resource.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <thread>
#include <unistd.h>

namespace native_io {
using Clock = std::chrono::steady_clock;
double now() { return std::chrono::duration<double>(Clock::now().time_since_epoch()).count(); }
struct Context {
    pid_t child = -1;
    int input_fd = -1, output_fd = -1, stderr_fd = -1, control_fd = -1;
    int child_status = -999, official_return = -999;
    int commands = 0;
    bool saw_zero = false, reaped = false, finalized = false;
    bool has_usage = false;
    double started = 0, deadline = 0, response_timeout = 5, next_command_deadline = 0;
    std::string buffered, error, error_kind, child_stderr;
    size_t offset = 0;
    struct rusage usage{};
    std::thread stderr_thread;
    std::atomic<bool> stop_stderr{false};
};
Context* context = nullptr;  // Heap lifetime survives std::exit from testlib.
volatile sig_atomic_t expired = 0;

std::string quote(const std::string& value) {
    std::string out = "\"";
    const char* hex = "0123456789abcdef";
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') { out += '\\'; out += c; }
        else if (c < 32 || c >= 127) {
            out += "\\u00"; out += hex[c >> 4]; out += hex[c & 15];
        } else out += c;
    }
    return out + '"';
}

void alarm_handler(int) {
    expired = 1;
    if (context && context->child > 0) kill(-context->child, SIGKILL);
}

void reap(bool force) {
    auto& c = *context;
    if (c.reaped || c.child <= 0) return;
    if (force) { kill(-c.child, SIGKILL); kill(c.child, SIGKILL); }
    int status;
    pid_t result;
    do { result = wait4(c.child, &status, force ? 0 : WNOHANG, &c.usage); }
    while (result < 0 && errno == EINTR);
    if (result == c.child) {
        c.reaped = c.has_usage = true;
        c.child_status = WIFEXITED(status) ? WEXITSTATUS(status) : -WTERMSIG(status);
    }
}

void finalize() {
    if (!context || context->finalized) return;
    auto& c = *context;
    c.finalized = true;
    struct itimerval disabled{};
    setitimer(ITIMER_REAL, &disabled, nullptr);
    if (expired && c.error.empty()) { c.error = "overall wall timeout exceeded"; c.error_kind = "timeout"; }
    reap(true);
    if (c.child > 0) kill(-c.child, SIGKILL);  // Also clean up inherited descendant pipes.
    if (c.input_fd >= 0) close(c.input_fd);
    if (c.output_fd >= 0) close(c.output_fd);
    c.stop_stderr = true;
    if (c.stderr_thread.joinable()) c.stderr_thread.join();
    if (c.stderr_fd >= 0) close(c.stderr_fd);
    std::ofstream err("solver_stderr.txt", std::ios::binary);
    err << c.child_stderr;
    err.close();
    if (tout.is_open()) tout.flush();
    struct rusage self{};
    getrusage(RUSAGE_SELF, &self);
    std::ostringstream report;
    report.precision(17);
    report << "{\"solver_pid\":" << c.child << ",\"solver_returncode\":" << c.child_status
           << ",\"official_returncode\":" << c.official_return
           << ",\"commands\":" << c.commands << ",\"saw_zero\":" << (c.saw_zero ? "true" : "false")
           << ",\"has_usage\":" << (c.has_usage ? "true" : "false")
           << ",\"cpu_user_s\":" << c.usage.ru_utime.tv_sec + c.usage.ru_utime.tv_usec / 1e6
           << ",\"cpu_system_s\":" << c.usage.ru_stime.tv_sec + c.usage.ru_stime.tv_usec / 1e6
           << ",\"maxrss_raw\":" << c.usage.ru_maxrss
           << ",\"self_cpu_user_s\":" << self.ru_utime.tv_sec + self.ru_utime.tv_usec / 1e6
           << ",\"self_cpu_system_s\":" << self.ru_stime.tv_sec + self.ru_stime.tv_usec / 1e6
           << ",\"self_maxrss_raw\":" << self.ru_maxrss
           << ",\"error\":" << quote(c.error) << ",\"error_kind\":" << quote(c.error_kind)
           << ",\"native_wall_s\":" << now() - c.started << "}\n";
    std::string payload = report.str();
    // This control fd is closed in the solver before exec. Resource reports
    // cannot be substituted by writing a file in the solver's working folder.
    if (c.control_fd >= 0) {
        size_t sent = 0;
        while (sent < payload.size()) {
            ssize_t n = write(c.control_fd, payload.data() + sent, payload.size() - sent);
            if (n < 0 && errno == EINTR) continue;
            if (n <= 0) break;
            sent += size_t(n);
        }
        close(c.control_fd); c.control_fd = -1;
    } else {
        std::ofstream file("native_report.json"); file << payload;
    }
}

[[noreturn]] void fail(const std::string& text, const std::string& kind = "protocol_error") {
    context->error = text;
    context->error_kind = kind;
    std::fprintf(stderr, "Native transport: %s\n", text.c_str());
    std::exit(3);
}

void deadline_check(double deadline, const char* message) {
    if (expired || now() >= deadline) fail(message, "timeout");
}

bool wait_readable(double deadline) {
    auto& c = *context;
    for (;;) {
        deadline_check(deadline, "solver did not flush a complete response before deadline");
        pollfd fd{c.output_fd, POLLIN, 0};
        int timeout = std::max(1, int(std::ceil((deadline - now()) * 1000)));
        int result = poll(&fd, 1, timeout);
        if (result > 0) return true;
        if (result < 0 && errno != EINTR) fail("stdout poll failed");
    }
}

std::string read_line(double deadline) {
    auto& c = *context;
    for (;;) {
        deadline_check(deadline, "solver did not flush a complete response before deadline");
        size_t end = c.buffered.find('\n', c.offset);
        size_t available = c.buffered.size() - c.offset;
        if (end != std::string::npos && end - c.offset + 1 <= 4096) {
            std::string line(c.buffered, c.offset, end - c.offset + 1);
            c.offset = end + 1;
            return line;
        }
        if (available >= 4097 || (end != std::string::npos && end - c.offset + 1 > 4096))
            fail("response line is too long or missing a newline");
        if (c.offset) { c.buffered.erase(0, c.offset); c.offset = 0; }
        wait_readable(deadline);
        char data[65536];
        ssize_t count = read(c.output_fd, data, sizeof(data));
        if (count == 0) {
            if (!c.buffered.empty()) fail("response line is too long or missing a newline");
            fail("solver closed stdout before replying");
        }
        if (count < 0) {
            if (errno == EINTR || errno == EAGAIN) continue;
            fail("stdout read failed");
        }
        c.buffered.append(data, size_t(count));
    }
}

bool blank(unsigned char c) { return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\v' || c == '\f'; }

std::string normalize(const std::string& line, int expected) {
    std::string out;
    size_t position = 0;
    int tokens = 0;
    while (position < line.size()) {
        while (position < line.size() && blank(line[position])) ++position;
        if (position == line.size()) break;
        size_t end = position;
        while (end < line.size() && !blank(line[end])) ++end;
        bool negative = line[position] == '-';
        size_t digits = position + (negative || line[position] == '+');
        if (digits == end) fail("response contains a non-integer token");
        for (size_t i = digits; i < end; ++i)
            if (line[i] < '0' || line[i] > '9') fail("response contains a non-integer token");
        while (digits < end && line[digits] == '0') ++digits;
        if (tokens++) out += ' ';
        if (digits == end) out += '0';
        else { if (negative) out += '-'; out.append(line, digits, end - digits); }
        position = end;
    }
    if (!tokens) fail("empty response line");
    if (tokens != expected) fail("wrong number of integer tokens on one response line");
    return out + '\n';
}

class ResponseReader : public InputStreamReader {
    std::string data;
    size_t pos = 0;
    int line = 1;
public:
    void reset(std::string value) { data = std::move(value); pos = 0; }
    int curChar() override { return pos < data.size() ? static_cast<unsigned char>(data[pos]) : EOFC; }
    int nextChar() override { int c = curChar(); if (pos < data.size()) { ++pos; if (c == '\n') ++line; } return c; }
    void skipChar() override { nextChar(); }
    void unreadChar(int c) override {
        if (!pos) fail("invalid testlib unread position");
        --pos; data[pos] = char(c); if (c == '\n') --line;
    }
    std::string getName() override { return "normalized solver stdout"; }
    bool eof() override { return pos >= data.size(); }
    void close() override {}
    int getLine() override { return line; }
};
ResponseReader* responses = nullptr;

void final_zero() {
    auto& c = *context;
    c.saw_zero = true;
    close(c.input_fd); c.input_fd = -1;
    double exit_deadline = std::min(c.deadline, now() + 2.0);
    while (!c.reaped) {
        deadline_check(exit_deadline, "solver did not terminate shortly after receiving 0");
        if (c.buffered.size() != c.offset) fail("solver wrote to stdout after receiving final 0");
        reap(false);
        if (c.reaped) break;
        pollfd fd{c.output_fd, POLLIN, 0};
        poll(&fd, 1, 1);
        if (fd.revents & (POLLIN | POLLHUP)) {
            char buffer[4097];
            ssize_t count = read(c.output_fd, buffer, sizeof(buffer));
            if (count > 0) fail("solver wrote to stdout after receiving final 0");
            if (count == 0) std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }
    if (c.buffered.size() != c.offset) fail("solver wrote to stdout after receiving final 0");
    // Same 0.2 s grace for EOF/late bytes as the reference harness.
    double drain_deadline = std::min(c.deadline, now() + 0.2);
    while (now() < drain_deadline) {
        pollfd fd{c.output_fd, POLLIN, 0};
        int result = poll(&fd, 1, std::max(1, int(std::ceil((drain_deadline - now()) * 1000))));
        if (result < 0 && errno == EINTR) continue;
        if (result <= 0) break;
        char buffer[4097];
        ssize_t count = read(c.output_fd, buffer, sizeof(buffer));
        if (count > 0) fail("solver wrote to stdout after receiving final 0");
        if (count == 0) break;
    }
}

class CommandBuffer : public std::streambuf {
    std::string command;
protected:
    int overflow(int c) override {
        if (c != traits_type::eof()) command += char(c);
        return traits_type::not_eof(c);
    }
    std::streamsize xsputn(const char* data, std::streamsize count) override {
        command.append(data, size_t(count)); return count;
    }
    int sync() override {
        if (context->finalized) return 0;
        if (command.empty()) return 0;
        auto& c = *context;
        deadline_check(c.deadline, "overall wall timeout exceeded");
        deadline_check(c.next_command_deadline, "interactor did not issue a command before deadline");
        if (command.size() > 4096 || command.back() != '\n') fail("malformed command from official checker");
        int value;
        try { value = std::stoi(command); } catch (...) { fail("malformed command from official checker"); }
        size_t sent = 0;
        while (sent < command.size()) {
            ssize_t count = write(c.input_fd, command.data() + sent, command.size() - sent);
            if (count < 0 && errno == EINTR) continue;
            if (count <= 0) fail("solver closed stdin before receiving command");
            sent += size_t(count);
        }
        ++c.commands;
        command.clear();
        if (value == 0) final_zero();
        else {
            responses->reset(normalize(read_line(std::min(c.deadline, now() + c.response_timeout)), value > 0 ? 2 : 1));
            c.next_command_deadline = std::min(c.deadline, now() + c.response_timeout);
        }
        return 0;
    }
};

void register_official(int argc, char** argv) {
    registerInteraction(argc, argv);
    if (ouf.reader) { ouf.reader->close(); delete ouf.reader; }
    responses = new ResponseReader();
    ouf.reader = responses;
}

void spawn(char** argv) {
    auto& c = *context;
    int input[2], output[2], errors[2], ready[2];
    if (pipe(input) || pipe(output) || pipe(errors) || pipe(ready)) fail("pipe failed");
    c.child = fork();
    if (c.child < 0) fail("fork failed");
    if (c.child == 0) {
        if (c.control_fd >= 0) close(c.control_fd);
        close(ready[1]); char token;
        if (read(ready[0], &token, 1) != 1) _exit(126);
        close(ready[0]);
        setsid();
        signal(SIGPIPE, SIG_DFL);
        dup2(input[0], STDIN_FILENO); dup2(output[1], STDOUT_FILENO); dup2(errors[1], STDERR_FILENO);
        for (int fd : {input[0], input[1], output[0], output[1], errors[0], errors[1]}) close(fd);
        execvp(argv[0], argv);
        dprintf(STDERR_FILENO, "exec failed: %s\n", strerror(errno));
        _exit(127);
    }
    close(ready[0]);
    if (c.control_fd >= 0) {
        std::string pid = std::to_string(c.child) + "\n";
        if (write(c.control_fd, pid.data(), pid.size()) != ssize_t(pid.size())) fail("control pipe failed");
    }
    close(input[0]); close(output[1]); close(errors[1]);
    c.input_fd = input[1]; c.output_fd = output[0]; c.stderr_fd = errors[0];
    write(ready[1], "x", 1); close(ready[1]);
    c.stderr_thread = std::thread([] {
        auto& c = *context;
        char buffer[65536];
        for (;;) {
            pollfd fd{c.stderr_fd, POLLIN, 0};
            int result = poll(&fd, 1, c.stop_stderr ? 0 : 20);
            if (result < 0 && errno == EINTR) continue;
            if (result <= 0) { if (c.stop_stderr) break; continue; }
            ssize_t count = read(c.stderr_fd, buffer, sizeof(buffer));
            if (count > 0) c.child_stderr.append(buffer, size_t(count));
            else if (!count || (errno != EINTR && errno != EAGAIN)) break;
        }
    });
}
}  // namespace native_io

#define main official_main
#define registerInteraction native_io::register_official
#include "official_checker.cpp"
#undef registerInteraction
#undef main

int main(int argc, char** argv) {
    if (argc < 9 || std::string(argv[7]) != "--") return 64;
    using namespace native_io;
    context = new Context();
    if (const char* control = std::getenv("PIPES_NATIVE_CONTROL_FD")) context->control_fd = std::stoi(control);
    context->started = now();
    context->response_timeout = std::stod(argv[5]);
    double wall = std::stod(argv[6]);
    context->deadline = context->started + wall;
    std::atexit(finalize);
    signal(SIGPIPE, SIG_IGN);
    spawn(argv + 8);
    context->next_command_deadline = std::min(context->deadline, now() + context->response_timeout);
    struct sigaction action{};
    action.sa_handler = alarm_handler;
    sigemptyset(&action.sa_mask);
    sigaction(SIGALRM, &action, nullptr);
    struct itimerval timer{};
    timer.it_value.tv_sec = int(wall);
    timer.it_value.tv_usec = int((wall - int(wall)) * 1e6);
    setitimer(ITIMER_REAL, &timer, nullptr);
    auto* command_buffer = new CommandBuffer();
    std::cout.rdbuf(command_buffer);
    int result = official_main(5, argv);
    context->official_return = result;
    deadline_check(context->deadline, "overall wall timeout exceeded");
    finalize();
    return result;
}
