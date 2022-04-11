export function handleCalls({ api, name, values, handler }) {
    let makeCall = (value) => api.call({ name, value });
    let calls = values.map((value) => () => makeCall(value));
    let firstCall = calls.shift();
    calls
        .reduce(
            (promise, fn) => {
                // intermediate calls handled here
                return promise.then((result) => {
                    handler(result);
                    return fn(result);
                });
            },
            firstCall() // first call is made seperately
        )
        .then((result) => {
            // a handler can be called to process the final result
            handler(result);
        })
        .catch((err) => {
            // errors handled here
            console.error(err);
        });
}