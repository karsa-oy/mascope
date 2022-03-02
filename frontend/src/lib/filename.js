
export function isValidFilename(string) {
    // Allow letters, numbers, space, underscore
    // Require at least one number or letter
    const valid_pattern = RegExp(/^[A-Za-z0-9 _]*[A-Za-z0-9][A-Za-z0-9 _]*$/);
    // Allow letters, numbers and underscore
    // const valid_pattern = RegExp(/^\w+$/);
    return valid_pattern.test(string);
}

export function makeValidFilename(string) {
    // Replace special characters with underscore
    return (string.replace(/[/|\\:*?"<>]/g, "_"));
}
