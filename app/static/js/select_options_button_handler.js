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