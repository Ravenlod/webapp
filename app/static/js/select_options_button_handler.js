 var select_options = document.getElementById("m_opt");
 var target_button = document.getElementById("ussd_request_hidden_button")
 var secondary_button = document.getElementById("cnl-btn")
 var input_value = document.getElementById("input_value")

    function ussdSessionCancel(event)
    {
        input_value.value = "ussd_cancel";

        alert("USSD session canceled");
    }

    secondary_button.addEventListener('click', ussdSessionCancel);
    function handleClick(event)
    {
        var selected_option = select_options.value
        if (selected_option === "ussd_option") {
            target_button.classList.remove("hidden")
        }
        else {
             target_button.classList.add("hidden")
        }
    }
    select_options.addEventListener("click", handleClick);

    //async functions
let copy_btn_click = document.querySelector('#copy_btn_1')
let text_field = document.querySelector('#copy_text_field')
let change_svg_btn = document.querySelector('#copy_btn_svg_1')

copy_btn_click.addEventListener('click', () => {
    let info = text_field.textContent;
    change_svg_btn.href = "#check2"; //Don't work
    navigator.clipboard.writeText(`${info}`);

})