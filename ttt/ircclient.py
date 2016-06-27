import irc
from irc.bot import ServerSpec, Channel
from irc.dict import IRCDict
from random import random

from ttt.reporter import Reporter


class IRCReporter(Reporter):

    def __init__(self, irc):
        self.irc = irc
        self.irc.connect()

    def wait(self):
        self.irc.poll()

    def halt(self):
        self.irc.disconnect()

    def report_build_failure(self):
        self.irc.say('TTT: Build failure!')

    def report_results(self, results):
        shortstats = '{} passed in {} seconds'.format(
            results['total_passed'],
            results['total_runtime']
        )
        total_failed = results['total_failed']
        if total_failed > 0:
            self.irc.say('TTT: {} failed, {}'.format(total_failed, shortstats))
        else:
            self.irc.say('TTT: {}'.format(shortstats))


class IRCClient(irc.client.SimpleIRCClient):
    """
    This class represents an IRC client that must have its poll() called
    periodically to process messages incoming from the IRC server. The client
    is limited in its ability to handle messages incoming from the IRC server
    and only has enough functionality to respond to PING events to maintain its
    connection.

    The primary role of the client is to act as a relay for the external caller
    calling poll() so that messages from that external caller are passed to the
    joined IRC channel.
    """
    # Heavily influenced by irc.client.SingleServerIRCBot and the example at
    # https://github.com/jaraco/irc/blob/master/scripts/testbot.py

    min_reconnect_wait = 1
    max_reconnect_wait = 10

    def __init__(self, channel, nickname, server, port=6667, **connect_params):
        super(IRCClient, self).__init__()
        if server is None:
            raise Exception("IRC Server not provided")
        self.__connect_params = connect_params
        self.channels = IRCDict()
        self.channel = channel
        self.server = ServerSpec(server, port)
        self._nickname = nickname
        assert 0 <= self.min_reconnect_wait <= self.max_reconnect_wait
        self._check_scheduled = False

        # Global handlers to handle channel/nick associations
        # Mostly when a nick is already in use
        for i in ["disconnect", "join", "kick", "mode",
                  "namreply", "nick", "part", "quit"]:
            self.connection.add_global_handler(
                i, getattr(self, "_on_" + i), -20
            )

    def _on_disconnect(self, c, e):
        self.channels = IRCDict()
        self.reconnect()

    def reconnect(self):
        """
        Called on a disconnect event to start a reconnection. The actual
        reconnection is deferred for some random amount of seconds.
        """
        def check():
            self._check_scheduled = False
            if not self.connection.is_connected():
                self.reconnect()
                if self.connection.is_connected():
                    self.disconnect()
                self.connect()

        if self._check_scheduled:
            return
        reconnect_wait = max(
            self.min_reconnect_wait,
            int(self.max_reconnect_wait * random())
        )
        self.connection.execute_delayed(reconnect_wait, check)
        self._check_scheduled = True

    def _on_join(self, c, e):
        ch = e.target
        nick = e.source.nick
        if nick == c.get_nickname():
            self.channels[ch] = Channel()
        self.channels[ch].add_user(nick)

    def _on_kick(self, c, e):
        nick = e.arguments[0]
        channel = e.target

        if nick == c.get_nickname():
            del self.channels[channel]
        else:
            self.channels[channel].remove_user(nick)

    def _on_mode(self, c, e):
        t = e.target
        if not irc.client.is_channel(t):
            # mode on self; disregard
            return
        ch = self.channels[t]

        modes = irc.modes.parse_channel_modes(" ".join(e.arguments))
        for sign, mode, argument in modes:
            f = {"+": ch.set_mode, "-": ch.clear_mode}[sign]
            f(mode, argument)

    def _on_namreply(self, c, e):
        """
        e.arguments[0] == "@" for secret channels,
                          "*" for private channels,
                          "=" for others (public channels)
        e.arguments[1] == channel
        e.arguments[2] == nick list
        """

        ch_type, channel, nick_list = e.arguments

        if channel == '*':
            # User is not in any visible channel
            # http://tools.ietf.org/html/rfc2812#section-3.2.5
            return

        for nick in nick_list.split():
            nick_modes = []

            if nick[0] in self.connection.features.prefix:
                nick_modes.append(self.connection.features.prefix[nick[0]])
                nick = nick[1:]

            for mode in nick_modes:
                self.channels[channel].set_mode(mode, nick)

            self.channels[channel].add_user(nick)

    def _on_nick(self, c, e):
        before = e.source.nick
        after = e.target
        for ch in self.channels.values():
            if ch.has_user(before):
                ch.change_nick(before, after)

    def _on_part(self, c, e):
        nick = e.source.nick
        channel = e.target

        if nick == c.get_nickname():
            del self.channels[channel]
        else:
            self.channels[channel].remove_user(nick)

    def _on_quit(self, c, e):
        nick = e.source.nick
        for ch in self.channels.values():
            if ch.has_user(nick):
                ch.remove_user(nick)

    def on_nicknameinuser(self, c, e):
        """
        When connecting it is discovered that the nick is already is use,
        provide an alternative.
        """
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        """
        Automatically join the channel once welcomed by the server.
        """
        c.join(self.channel)

    def on_privmsg(self, c, e):
        """
        Disable private messaging with users.
        """
        nick = e.source.nick
        msg = "I am sorry, {}; I do not do private messages.".format(nick)
        c.notice(nick, msg)

    def on_dccmsg(self, c, e):
        """
        Disable dcc messaging with users.
        """
        nick = e.source.nick
        # text = e.arguments[0].decode('utf-8')
        msg = "I am sorry, {}; I do not do dcc messages.".format(nick)
        c.privmsg(nick, msg)

    def disconnect(self):
        self.connection.disconnect("Bye!")

    def get_version(self):
        return "ttt irc reporter ({version})".format(
            version=irc.client.VERSION_STRING)

    def on_ctcp(self, c, e):
        nick = e.source.nick
        if e.arguments[0] == "VERSION":
            c.ctcp_reply(nick, "VERSION " + self.get_version())
        elif e.arguments[0] == "PING":
            if len(e.arguments) > 1:
                c.ctcp_reply(nick, "PING " + e.arguments[1])

    def poll(self):
        """
        Poll the IRC connection for events. The reactor processing uses select
        on the socket so give a 0.2s timeout so that control returns.

        Polling must occur or else the IRC server will likely disconnect the
        client due to ping timeout.
        """
        self.reactor.process_once(0.2)

    def connect(self):
        server = self.server
        try:
            super(IRCClient, self).connect(
                server.host,
                server.port,
                self._nickname,
                server.password,
                username=self._nickname,
                ircname=self._nickname,
                **self.__connect_params
            )
        except irc.client.ServerConnectionError:
            self.reconnect()  # Schedule a deferred reconnection retry
            pass

    def say(self, message):
        """
        The main interface into this client (other than poll() and connect())
        to send messages from the external caller to the IRC channel.

        If there happens to be no connection when something is said, then say
        nothing. A (re)connection is either happening or the server is down.
        Note that this is an issue only because a message is sent to the IRC
        server explicitly and not a handler reacting to something the server
        has sent (which requires that the connection is up to occur).
        """
        try:
            self.connection.privmsg(self.channel, message)
        except irc.client.ServerNotConnectedError:
            # Connection down? Try a reconnect, and skip saying anything. The
            # time to say it has already passed.
            self.reconnect()
            pass


class _IRCClient(IRCClient):
    def on_pubmsg(self, c, e):
        nick = e.source.nick
        print("{}: {}".format(nick, e.arguments[0]))


def main():
    import sys
    import argparse
    import jaraco.logging
    import threading
    import queue

    parser = argparse.ArgumentParser()
    parser.add_argument('server')
    parser.add_argument('port', type=int)
    parser.add_argument('channel')
    parser.add_argument('nickname')
    jaraco.logging.add_arguments(parser)
    args = parser.parse_args()
    jaraco.logging.setup(args)

    irc_reporter = _IRCClient(args.channel,
                              args.nickname,
                              args.server,
                              args.port)
    irc_reporter.connect()

    def read_input(stream, q):
        for line in iter(stream.readline, b''):
            q.put(line.strip())

    inputq = queue.Queue()
    input_thread = threading.Thread(target=read_input,
                                    args=(sys.stdin, inputq))
    input_thread.daemon = True  # Kill thread on main thread exit
    input_thread.start()
    try:
        while True:
            irc_reporter.poll()
            try:
                irc_reporter.say(inputq.get_nowait())
            except queue.Empty:
                pass
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        irc_reporter.disconnect()

if __name__ == "__main__":
    main()
