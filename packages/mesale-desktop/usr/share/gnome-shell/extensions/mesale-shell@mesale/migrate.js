// One-time changes to settings a user may already have, run once per Mesale version
// of the defaults. Each step runs only once, so a choice the user makes later stays.
import Gio from 'gi://Gio';

function schema(id) {
    const source = Gio.SettingsSchemaSource.get_default();
    return source?.lookup(id, true) ? new Gio.Settings({schema_id: id}) : null;
}

const STEPS = [
    // 1: Super+1..9 are workspaces now. Dash to Panel may have written its own
    // Super+number app keys into the user's settings, which beat the new default.
    () => {
        const panel = schema('org.gnome.shell.extensions.dash-to-panel');
        if (panel?.settings_schema.has_key('hot-keys'))
            panel.set_boolean('hot-keys', false);
    },
];

export function run(settings) {
    const done = settings.get_int('settings-steps');
    for (let step = done; step < STEPS.length; step++) {
        try {
            STEPS[step]();
        } catch (e) {
            logError(e, `Mesale Shell: settings step ${step + 1}`);
        }
    }
    if (done < STEPS.length)
        settings.set_int('settings-steps', STEPS.length);
}
