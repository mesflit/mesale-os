// Node module hooks: GNOME's gi:// and resource:// imports become stand-ins, so the
// extension's modules load in plain Node and missing files or exports show up.
export async function resolve(specifier, context, next) {
    if (specifier.startsWith('gi://') || specifier.startsWith('resource://'))
        return {url: `stub:${specifier}`, shortCircuit: true};
    return next(specifier, context);
}

// Anything: callable, constructible, every property is another stand-in
const STAND_IN = `
const any = new Proxy(function () {}, {
    get: (_t, key) => key === Symbol.toPrimitive ? () => '' : key === 'then' ? undefined : any,
    apply: () => any,
    construct: () => any,
});
export default any;
export const Extension = class {};
`;

export async function load(url, context, next) {
    if (url.startsWith('stub:'))
        return {format: 'module', source: STAND_IN, shortCircuit: true};
    return next(url, context);
}
