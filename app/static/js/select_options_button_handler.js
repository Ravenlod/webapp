
async function postJSON(path, method, data = null) {
  returnData = null
  try 
  {
    const response = await fetch(String(path), {
      method: method,
      headers: {
        "Content-Type": "application/json",
      },
      body: (data !== null) ? JSON.stringify(data): undefined,
    })
    .then(response => 
    {
      if (response.status !== 200) 
      {
          console.log('Ошибка: ' + response.status);
      }
    return response.json();
    })
    .then(data => 
    {
      returnData = data;
    })
    return returnData;
  } 
  catch (error) 
  {
    console.error("Error:", error);
  }

}

let copy_buttons = document.querySelectorAll('.copy-btn');


copy_buttons.forEach( (copy_btn) => 
{

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



