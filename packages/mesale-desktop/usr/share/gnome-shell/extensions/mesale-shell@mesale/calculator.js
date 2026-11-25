// Arithmetic for the command bar: a small recursive descent parser, no eval.
export function calculate(text) {
    if (!/^[\d\s.,+\-*/%^()]+$/.test(text) || !/[+\-*/%^]/.test(text))
        return null;
    const input = text.replace(/,/g, '.').replace(/\s/g, '');
    let pos = 0;

    const sum = () => {
        let value = product();
        while (input[pos] === '+' || input[pos] === '-')
            value = input[pos++] === '+' ? value + product() : value - product();
        return value;
    };
    const product = () => {
        let value = power();
        while ('*/%'.includes(input[pos] ?? '?')) {
            const operator = input[pos++], right = power();
            value = operator === '*' ? value * right : operator === '/' ? value / right : value % right;
        }
        return value;
    };
    const power = () => {
        const value = atom();
        if (input[pos] !== '^')
            return value;
        pos++;
        return value ** power();
    };
    const atom = () => {
        if (input[pos] === '-') {
            pos++;
            return -power();
        }
        if (input[pos] === '(') {
            pos++;
            const value = sum();
            return input[pos++] === ')' ? value : NaN;
        }
        const number = /^\d*\.?\d+|^\d+\.?/.exec(input.slice(pos));
        if (!number)
            return NaN;
        pos += number[0].length;
        return parseFloat(number[0]);
    };

    const result = sum();
    return pos === input.length && Number.isFinite(result) ? String(+result.toPrecision(12)) : null;
}
