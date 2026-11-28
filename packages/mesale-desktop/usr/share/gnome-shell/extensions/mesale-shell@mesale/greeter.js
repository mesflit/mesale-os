// The login screen follows the wallpaper. When picture-uri changes (from Mesale Center,
// GNOME Settings or anywhere else), make-greeter turns it into a blurred picture as the
// user and set-greeter puts it in place through pkexec (allowed without a password for
// the person at the computer, see org.mesale.greeter.policy). Both run outside the
// shell, so it never waits on them.
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

const MAKE = '/usr/lib/mesale/make-greeter';
const SET = '/usr/lib/mesale/set-greeter';
const WAIT_S = 2;   // a few quick clicks in a row make one update

export class GreeterSync {
    constructor(settings) {
        this._settings = settings;   // org.mesale.shell: greeter-source remembers the last one done
        this._background = new Gio.Settings({schema_id: 'org.gnome.desktop.background'});
        this._background.connectObject('changed::picture-uri', () => this._queue(), this);
        this._timer = 0;
        this._queue();   // catch up on a change made while logged out
    }

    _queue() {
        if (this._timer)
            GLib.source_remove(this._timer);
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_LOW, WAIT_S, () => {
            this._timer = 0;
            this._update();
            return GLib.SOURCE_REMOVE;
        });
    }

    _update() {
        const uri = this._background.get_string('picture-uri');
        if (!uri || uri === this._settings.get_string('greeter-source') ||
            !GLib.file_test(MAKE, GLib.FileTest.IS_EXECUTABLE))
            return;
        try {
            // The wallpaper's address goes in as an argument ("$1"), never into the shell text
            const process = Gio.Subprocess.new(['sh', '-c', `"${MAKE}" "$1" | pkexec "${SET}"`, 'sh', uri],
                Gio.SubprocessFlags.STDERR_PIPE);
            process.communicate_utf8_async(null, null, (_p, result) => {
                try {
                    const [, , errors] = process.communicate_utf8_finish(result);
                    if (process.get_successful())
                        this._settings.set_string('greeter-source', uri);
                    else
                        log(`Mesale Shell: login screen not updated: ${errors?.trim()}`);
                } catch (e) {
                    logError(e, 'Mesale Shell: login screen');
                }
            });
        } catch (e) {
            logError(e, 'Mesale Shell: login screen');
        }
    }

    destroy() {
        if (this._timer)
            GLib.source_remove(this._timer);
        this._timer = 0;
        this._background.disconnectObject(this);
    }
}
