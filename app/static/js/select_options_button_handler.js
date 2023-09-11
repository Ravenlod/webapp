var secondary_button = document.getElementById("cnl-btn");
var input_value = document.getElementById("input_value");
var con_switch = document.getElementById('connectionSwitch_1');

if (secondary_button != null){
    secondary_button.addEventListener('click', () => {
    input_value.value = "ussd_cancel";
    alert("USSD session canceled");
    });
}


con_switch.addEventListener('click', () => {
    var state = !con_switch.checked;
    // const data = {state: state};
    fetch("/settings/switch", {
        method: "POST",
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({"status": state})
    })
    //.then(responseData => console.log('Server response:', responseData))
    .then(response => {if(!response.ok){
                            throw new Error('Network response Error');}
                       response.json(); })

    .catch(error => {
        console.error("Error:", error);

    });
});

    //async functions
let copy_btn = document.getElementsByClassName('copy-btn');


for(let i = 0; i < copy_btn.length; i ++)
{
    let text_field = document.querySelector('#copy_text_field_' + String(copy_btn[i].getAttribute('value')));
    let change_svg_btn = document.querySelector('#copy_btn_svg_'+ String(copy_btn[i].getAttribute('value')));



    copy_btn[i].addEventListener('click', () => {
    // + String(copy_btn_click.getAttribute('value')));
   //+ String(copy_btn_click.getAttribute('value')));

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
}


