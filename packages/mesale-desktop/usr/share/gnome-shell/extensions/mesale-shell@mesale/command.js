// Command bar (Super+Space): apps, windows, settings, math, system actions.
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import Shell from 'gi://Shell';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as SystemActions from 'resource:///org/gnome/shell/misc/systemActions.js';

const TR = (GLib.get_language_names()[0] ?? 'en').startsWith('tr');
const EN = {'Ara, aç, hesapla…': 'Search, open, calculate…', 'Kopyala': 'Copy', 'Uygulama': 'App', 'Pencere': 'Window', 'Ayar': 'Setting', 'Ekranı kilitle': 'Lock screen', 'Kapat': 'Power off', 'Yeniden başlat': 'Restart', 'Askıya al (uyku)': 'Suspend', 'Oturumu kapat': 'Log out', 'Ekran görüntüsü': 'Screenshot', 'Eylem': 'Action', 'Yükle': 'Install'};
const T = s => TR ? s : EN[s] ?? s;

const EN_FAZLA = 7;
// Lower case (Turkish aware), accent-insensitive
const sade = s => s.toLocaleLowerCase('tr').normalize('NFD').replace(/\p{M}/gu, '').replace(/ı/g, 'i');

// Arithmetic: small recursive parser, no eval
function hesapla(m) {
    if (!/^[\d\s.,+\-*/%^()]+$/.test(m) || !/[+\-*/%^]/.test(m))
        return null;
    const s = m.replace(/,/g, '.').replace(/\s/g, '');
    let i = 0;
    const toplam = () => {
        let d = carpim();
        while (s[i] === '+' || s[i] === '-')
            d = s[i++] === '+' ? d + carpim() : d - carpim();
        return d;
    };
    const carpim = () => {
        let d = us();
        while ('*/%'.includes(s[i] ?? '?')) {
            const o = s[i++], r = us();
            d = o === '*' ? d * r : o === '/' ? d / r : d % r;
        }
        return d;
    };
    const us = () => {
        const d = birim();
        return s[i] === '^' ? (i++, d ** us()) : d;
    };
    const birim = () => {
        if (s[i] === '-')
            return i++, -us();
        if (s[i] === '(') {
            i++;
            const d = toplam();
            return s[i++] === ')' ? d : NaN;
        }
        const n = /^\d*\.?\d+|^\d+\.?/.exec(s.slice(i));
        if (!n)
            return NaN;
        i += n[0].length;
        return parseFloat(n[0]);
    };
    const d = toplam();
    return i === s.length && Number.isFinite(d) ? String(+d.toPrecision(12)) : null;
}

export const KomutCubugu = GObject.registerClass(
class KomutCubugu extends St.Widget {
    _init() {
        super._init({visible: false, reactive: true, layout_manager: new Clutter.BinLayout()});
        // Whole-screen blur behind the bar (rectangular, so no corner artefacts)
        this._bugu = new St.Widget({x_expand: true, y_expand: true});
        this._bugu.add_effect(new Shell.BlurEffect({mode: Shell.BlurMode.BACKGROUND, radius: 40, brightness: 0.96}));
        this.add_child(this._bugu);
        this._kutu = new St.BoxLayout({style_class: 'mesale-komut', orientation: Clutter.Orientation.VERTICAL, reactive: true,
            x_align: Clutter.ActorAlign.CENTER, y_align: Clutter.ActorAlign.END, x_expand: true, y_expand: true});
        this._giris = new St.Entry({style_class: 'mesale-giris', hint_text: T('Ara, aç, hesapla…'), can_focus: true, x_expand: true});
        this._giris.set_primary_icon(new St.Icon({icon_name: 'system-search-symbolic', icon_size: 18}));
        this._liste = new St.BoxLayout({style_class: 'mesale-liste', orientation: Clutter.Orientation.VERTICAL});
        this._kutu.add_child(this._liste);
        this._kutu.add_child(this._giris);
        this.add_child(this._kutu);
        Main.layoutManager.addTopChrome(this);
        this.hide();

        this._giris.clutter_text.connect('text-changed', () => this._ara());
        this._giris.clutter_text.connect('activate', () => this._calistir());
        this._giris.clutter_text.connect('key-press-event', (_a, o) => this._tus(o));
        const tik = new Clutter.ClickGesture();
        tik.connect('recognize', () => {
            const [x, y] = global.get_pointer();
            const k = this._kutu.get_transformed_extents();
            if (x < k.get_x() || y < k.get_y() || x > k.get_x() + k.get_width() || y > k.get_y() + k.get_height())
                this.kapat();
        });
        this.add_action(tik);
    }

    renkAyarla(acik) {
        this._kutu.style = acik
            ? 'background-color: rgba(255,255,255,0.72); color: #16243d; border-color: rgba(255,255,255,0.8);'
            : 'background-color: rgba(18,27,54,0.72); color: #eef4ff; border-color: rgba(190,210,255,0.18);';
    }

    acKapat() {
        if (this.visible)
            this.kapat();
        else
            this._ac();
    }

    _ac() {
        const m = Main.layoutManager.primaryMonitor;
        this.set_position(m.x, m.y);
        this.set_size(m.width, m.height);
        this._kutu.translation_y = -84; 
        this.show();
        this._kilit = Main.pushModal(this, {actionMode: Shell.ActionMode.POPUP});
        if (!this._kilit) {
            this.kapat();
            return;
        }
        this._giris.set_text('');
        this._ara();
        this._giris.grab_key_focus();
        this.opacity = 0;
        this._kutu.translation_y = -60;
        this.ease({opacity: 255, duration: 130, mode: Clutter.AnimationMode.EASE_OUT_QUAD});
        this._kutu.ease({translation_y: -84, duration: 190, mode: Clutter.AnimationMode.EASE_OUT_CUBIC});
    }

    kapat() {
        if (this._kilit) {
            Main.popModal(this._kilit);
            this._kilit = null;
        }
        this.hide();
    }

    _tus(o) {
        switch (o.get_key_symbol()) {
        case Clutter.KEY_Escape:
            this.kapat();
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Down:
        case Clutter.KEY_Tab:
            this._sec(this._secili + 1);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Up:
        case Clutter.KEY_ISO_Left_Tab:
            this._sec(this._secili - 1);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_space:
            if (o.get_state() & Clutter.ModifierType.MOD4_MASK) {
                this.kapat();
                return Clutter.EVENT_STOP;
            }
        }
        return Clutter.EVENT_PROPAGATE;
    }

    _adaylar(ham) {
        const q = sade(ham.trim());
        const son = [];
        const ekle = (ad, tur, simge, calistir) => son.length < EN_FAZLA && son.push({ad, tur, simge, calistir});

        const sonuc = hesapla(ham.trim());
        if (sonuc !== null) {
            ekle(`= ${sonuc}`, T('Kopyala'), 'accessories-calculator-symbolic', () =>
                St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, sonuc));
        }
        const sistem = Shell.AppSystem.get_default();
        if (!q) {
            for (const id of global.settings.get_strv('favorite-apps')) {
                const u = sistem.lookup_app(id);
                if (u)
                    ekle(u.get_name(), T('Uygulama'), u.get_icon(), () => u.activate());
            }
            return son;
        }
        for (const w of global.display.list_all_windows()) {
            if (!w.skip_taskbar && w.title && sade(w.title).includes(q)) {
                const u = Shell.WindowTracker.get_default().get_window_app(w);
                ekle(w.title, T('Pencere'), u?.get_icon() ?? 'window-symbolic', () => Main.activateWindow(w));
            }
            if (son.length >= 3)
                break;
        }
        const gorulen = new Set();
        for (const grup of Shell.AppSystem.search(q).concat(ham === q ? [] : Shell.AppSystem.search(ham))) {
            for (const id of grup) {
                const u = sistem.lookup_app(id);
                if (u && !gorulen.has(id) && u.get_app_info().should_show()) {
                    gorulen.add(id);
                    ekle(u.get_name(), T('Uygulama'), u.get_icon(), () => u.activate());
                }
            }
        }
        for (const i of Gio.AppInfo.get_all()) {
            const id = i.get_id() ?? '';
            if (/^gnome-.*-panel\.desktop$/.test(id) && sade(`${i.get_name()} ${i.get_keywords?.().join(' ') ?? ''}`).includes(q))
                ekle(i.get_name(), T('Ayar'), i.get_icon(), () => i.launch([], global.create_app_launch_context(0, -1)));
        }
        const e = SystemActions.getDefault();
        for (const [ad, simge, is] of [
            [T('Ekranı kilitle'), 'system-lock-screen-symbolic', () => e.activateLockScreen()],
            [T('Kapat'), 'system-shutdown-symbolic', () => e.activatePowerOff()],
            [T('Yeniden başlat'), 'system-reboot-symbolic', () => e.activateRestart()],
            [T('Askıya al (uyku)'), 'weather-clear-night-symbolic', () => e.activateSuspend()],
            [T('Oturumu kapat'), 'system-log-out-symbolic', () => e.activateLogout()],
            [T('Ekran görüntüsü'), 'camera-photo-symbolic', () => Main.screenshotUI.open()],
        ]) {
            if (sade(ad).includes(q))
                ekle(ad, T('Eylem'), simge, is);
        }
        ekle(TR ? `“${ham.trim()}” için Yazılım’da ara` : `Search Software for “${ham.trim()}”`, T('Yükle'), 'software-install-symbolic', () =>
            GLib.spawn_async(null, ['gnome-software', `--search=${ham.trim()}`], null, GLib.SpawnFlags.SEARCH_PATH, null));
        return son;
    }

    _ara() {
        this._liste.destroy_all_children();
        this._aday = this._adaylar(this._giris.get_text());
        this._aday.forEach((a, n) => {
            const satir = new St.Button({style_class: 'mesale-satir', x_expand: true});
            const ic = new St.BoxLayout({x_expand: true, style: 'spacing: 12px;'});
            const simge = new St.Icon({icon_size: 26, y_align: Clutter.ActorAlign.CENTER});
            if (typeof a.simge === 'string')
                simge.icon_name = a.simge;
            else
                simge.gicon = a.simge;
            ic.add_child(simge);
            ic.add_child(new St.Label({text: a.ad, x_expand: true, y_align: Clutter.ActorAlign.CENTER}));
            ic.add_child(new St.Label({text: a.tur, style_class: 'mesale-tur', y_align: Clutter.ActorAlign.CENTER}));
            satir.set_child(ic);
            satir.connect('clicked', () => {
                this._secili = n;
                this._calistir();
            });
            this._liste.add_child(satir);
        });
        this._sec(0);
    }

    _sec(n) {
        const c = this._liste.get_children();
        if (!c.length)
            return;
        this._secili = (n + c.length) % c.length;
        c.forEach((s, i) => i === this._secili ? s.add_style_class_name('secili') : s.remove_style_class_name('secili'));
    }

    _calistir() {
        const a = this._aday[this._secili];
        this.kapat();
        a?.calistir();
    }
});
