
async function postJSON(path, data, method) {
  try {
    const response = await fetch(String(path), {
      method: method,
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })
    .catch(error => {
      console.error("Error:", error);})

    //const result = await response.json();
    //console.log("Success:", result);
  } catch (error) {
    console.error("Error:", error);
  }
}

    //async functions
let copy_buttons = document.querySelectorAll('.copy-btn');


copy_buttons.forEach( (copy_btn) => {

    //let text_field = document.querySelector('#copy_text_field_' + String(copy_btn.getAttribute('value')));
    //let change_svg_btn = document.querySelector('#copy_btn_svg_'+ String(copy_btn.getAttribute('value')));
    let change_svg_btn = copy_btn.querySelector('.copy_btn_svg')
    let text_field = copy_btn.closest('.copy-container').querySelector('.copy_text_field')

    copy_btn.addEventListener('click', () => {

    if (window.isSecureContext) {
        let info = text_field.textContent;
        navigator.clipboard.writeText(`${info}`).then();
    }
    else {
        var range = document.createRange();
        range.selectNodeContents(text_field);
        var selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        document.execCommand('copy');
        selection.removeAllRanges();
    }
    change_svg_btn.setAttribute("href", "#check2");
    setTimeout(() =>{change_svg_btn.setAttribute("href", "#clipboard")}, 5000)

    })


})



