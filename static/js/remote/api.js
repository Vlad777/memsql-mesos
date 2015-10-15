var $ = require('jquery');

class Api {
    call(path, params) {
        return new Promise((resolve, reject) => {
            $.ajax("api/" + path, {
                method: "POST",
                data: JSON.stringify(params),
                dataType: "json",
                success: resolve,
                error: (xhr, status, error) => {
                    if (status === "error") {
                        reject(xhr.responseJSON);
                    } else {
                        reject(new Error("Api call failure due to " + status + ": " + error));
                    }
                }
            });
        });
    }
}

module.exports = new Api();
