$('#game-searchbar').autocomplete({
    lookup: {{ app_id_to_name | safe }},
    triggerSelectOnValidInput: false,
    minChars: 2,
    onSelect: function(suggestion) {
    	var user_vector = "";
    	if ($('#user-vector-toggle').prop('checked'))
    		user_vector = "&user_vector=on";

        window.location = "/?app_id=" + suggestion.data + user_vector;
    }
});
