(function () {
  "use strict";

  var root = document.getElementById("editor-root");
  if (!root) return;

  var hidden = document.getElementById(root.dataset.targetField);
  var csrfToken = root.dataset.csrfToken;

  var quill = new Quill("#editor-root", {
    theme: "snow",
    modules: {
      toolbar: [
        [{ header: [2, 3, 4, false] }],
        ["bold", "italic", "underline", "strike"],
        [{ list: "ordered" }, { list: "bullet" }],
        [{ align: [] }],
        [{ indent: "-1" }, { indent: "+1" }],
        ["blockquote", "code-block"],
        ["link"],
        ["clean"],
      ],
    },
  });

  // Treść początkowa wstrzykiwana przez dangerouslyPasteHTML, a nie innerHTML —
  // Quill sam ją parsuje do swojego modelu. Źródłem jest body_source, który
  // i tak przechodzi przez bleach po stronie serwera przy zapisie.
  var initial = document.getElementById("initial-content");
  if (initial && initial.value) {
    quill.clipboard.dangerouslyPasteHTML(initial.value);
  }

  function syncHidden() {
    hidden.value = quill.root.innerHTML;
  }

  quill.on("text-change", syncHidden);
  syncHidden();

  document.querySelector("form").addEventListener("submit", syncHidden);

  function post(url, body, onSuccess) {
    fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken },
      body: body,
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          window.alert(result.data.error || "Operacja nie powiodła się.");
          return;
        }
        onSuccess(result.data);
      })
      .catch(function () {
        window.alert("Błąd połączenia z serwerem.");
      });
  }

  function insertAtCursor(callback) {
    var range = quill.getSelection(true);
    callback(range ? range.index : quill.getLength());
  }

  var fileInput = document.getElementById("image-upload");
  if (fileInput) {
    fileInput.addEventListener("change", function () {
      if (!fileInput.files.length) return;
      var data = new FormData();
      data.append("file", fileInput.files[0]);
      post(fileInput.dataset.endpoint, data, function (payload) {
        insertAtCursor(function (index) {
          quill.insertEmbed(index, "image", payload.url, "user");
        });
        syncHidden();
      });
      fileInput.value = "";
    });
  }

  var embedButton = document.getElementById("embed-youtube");
  if (embedButton) {
    embedButton.addEventListener("click", function () {
      var url = window.prompt("Wklej adres filmu na YouTube:");
      if (!url) return;
      var data = new FormData();
      data.append("url", url);
      post(embedButton.dataset.endpoint, data, function (payload) {
        // Serwer zwraca placeholder (<div data-youtube-id>), nie iframe —
        // na ramkę zamienia go dopiero render przy wyświetlaniu wpisu.
        insertAtCursor(function (index) {
          quill.clipboard.dangerouslyPasteHTML(index, payload.html, "user");
        });
        syncHidden();
      });
    });
  }

  var urlButton = document.getElementById("image-by-url");
  if (urlButton) {
    urlButton.addEventListener("click", function () {
      var url = window.prompt("Wklej adres obrazka (tylko zaufane domeny):");
      if (!url) return;
      var data = new FormData();
      data.append("url", url);
      post(urlButton.dataset.endpoint, data, function (payload) {
        insertAtCursor(function (index) {
          quill.insertEmbed(index, "image", payload.url, "user");
        });
        syncHidden();
      });
    });
  }
})();
