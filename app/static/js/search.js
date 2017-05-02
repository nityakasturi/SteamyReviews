$(document).ready(function() {
    // Page setup
    var attributeChart = $(".details-attribute-chart");
    var currentGameVector;
    var detailsExpanded = false;
    var detailsRadarChart;
    var removedFeaturesIdx = [];
    var selectedAppID;
    var unselected = [];

    if (userAccount != "None") {
        $(".user-menu").fadeIn(150).css("display", "inline-block");
        $('#user-vector-toggle').bootstrapToggle({
            on: 'Yes',
            off: 'No'
        });
        $('#user-vector-toggle').bootstrapToggle(vector_toggle);
    } else
        $(".user-login").fadeIn(150).css("display", "inline-block");

    if (currentGameTitle !== undefined) {
        $('html, body').animate({
            scrollTop: $(".global-search").offset().top - 15
        }, 400);
    }
    if (currentGameTitle !== undefined || "{{ library_vector }}" !== undefined) {
        var queryString = window.location.search;
        queryString = queryString.substring(1);

        var parseQueryString = function(queryString) {
            var params = {},
                queries, temp, i, l;
            // Split into key/value pairs
            queries = queryString.split("&");
            // Convert the array of strings into an object
            for (i = 0, l = queries.length; i < l; i++) {
                temp = queries[i].split('=');
                params[temp[0]] = decodeURI(temp[1]);
            }
            return params;
        };
        var parsed = parseQueryString(queryString);
        if ('removed_features' in parsed) {
            unselected = atob(parseQueryString(queryString)['removed_features']).split(',');
        } else {
            unselected = null;
        }

        var tags_div = $(".tags");
        var search_tags = tags_div.data("tags");
        for (var key in search_tags) {
            if (!search_tags.hasOwnProperty(key)) continue;
            var value = search_tags[key];
            if (unselected !== null && unselected.indexOf(value) !== -1) {
                tags_div.append("<p class='tag'>" + value +
                    "<span class='glyphicon glyphicon-remove tag-icon' aria-hidden='true'></span></p>");

                var foundIdx = currentGameFeatureNames.indexOf(value);
                if (foundIdx != -1) {
                    currentGameFeatureNames = currentGameFeatureNames.slice(0, foundIdx)
                        .concat(currentGameFeatureNames.slice(foundIdx + 1, currentGameFeatureNames.length));
                    currentGameFeatures = currentGameFeatures.slice(0, foundIdx)
                        .concat(currentGameFeatures.slice(foundIdx + 1, currentGameFeatures.length));
                    removedFeaturesIdx.push(foundIdx);
                }
            } else {
                tags_div.append("<p class='tag selected'>" + value +
                    "<span class='glyphicon glyphicon-ok tag-icon' aria-hidden='true'></span></p>");
            }
        }
        tags_div.append("<button type='submit' class='btn btn-desc feature-btn' style='display: block; margin: 0 auto;'>Apply changes</button>")

    }

    if (toggle_modal !== undefined) {
        $("#login-modal").modal();
        $('.login-input').focus();
    }

    if (vector_toggle == "on") {
        $('.no-vector-ranking').css("display", "none");
        $('.vector-ranking').css("display", "block");
    }

    // Handle event listeners

    // Thanks to: http://stackoverflow.com/questions/28631219/how-can-i-unfocus-the-modal-trigger-button-after-closing-the-modal-in-bootstrap
    $("#login-modal").on("shown.bs.modal", function(e) {
        $('.user-login').one('focus', function(e) {
            $(this).blur();
        });
        $('.login-input').focus();
    });

    $(".details-close").click(function() {
        $(".details-content-wrapper").fadeOut(150, function() {
            $(".details-overlay").animate({
                width: '0px'
            }, 300);
            detailsExpanded = false;
        });
    });

    $(".details-query").click(function() {
        var user_vector = "";
        if ($('#user-vector-toggle').prop('checked'))
            user_vector = "&user_vector=on";

        window.location.replace("/?app_id=" + selectedAppID + user_vector);
    });

    $(".logout").click(function() {
        document.cookie = 'username=;expires=Thu, 01 Jan 1970 00:00:01 GMT;';
        document.cookie = 'library_vector=;expires=Thu, 01 Jan 1970 00:00:01 GMT;';
        document.cookie = 'steam_ID=;expires=Thu, 01 Jan 1970 00:00:01 GMT;';
        location.reload();
    });

    var userVectorToggle = $('#user-vector-toggle');
    userVectorToggle.change(function() {
        if (userVectorToggle.prop('checked')) {
            $('.no-vector-ranking').fadeOut(150, function() {
                $('.vector-ranking').fadeIn(150);
            });
        } else {
            $('.vector-ranking').fadeOut(150, function() {
                $('.no-vector-ranking').fadeIn(150);
            });
        };
        updateDetails()
    })

    var resultBox = $(".result-box");
    var updateDetails = function() {
        var gameTitle = resultBox.data("title");
        $(".details-title").text(gameTitle);
        $(".details-score-num").text((resultBox.data("score") * 100).toFixed(1) + "%");
        $(".details-img").attr("src", resultBox.children(".result-img").attr("src"));
        $(".details-link").attr("href", resultBox.data("steam-url"));

        var tagsDiv = $(".details-tags");
        tagsDiv.empty();
        $.each(JSON.parse(atob(resultBox.data("tags"))), function(index, tag) {
            tagsDiv.append("<p class='tag unselectable'>" + tag + "</p>");
        });
        selectedAppID = resultBox.data("app-id");

        var gameVector = resultBox.data("features").map(Math.log);

        for (idx = 0; idx < removedFeaturesIdx.length; idx += 1) {
            var feature = removedFeaturesIdx[idx];
            gameVector = gameVector.slice(0, feature)
                .concat(gameVector.slice(feature + 1, gameVector.length));
        }

        var queryVector;
        if (offsetVector !== null && userVectorToggle.prop('checked')) {
            queryVector = offsetVector;
        } else {
            queryVector = gameVector;
        }

        console.log(queryVector);

        var data = {
            labels: currentGameFeatureNames,
            datasets: [{
                label: gameTitle,
                backgroundColor: "rgba(255,99,132,0.2)",
                borderColor: "rgba(255,99,132,1)",
                pointBackgroundColor: "rgba(255,99,132,1)",
                pointBorderColor: "#fff",
                pointHoverBackgroundColor: "#fff",
                pointHoverBorderColor: "rgba(255,99,132,1)",
                data: gameVector
            }, {
                label: currentGameTitle,
                backgroundColor: "rgba(90, 179, 206, 0.2)",
                borderColor: "rgba(90, 179, 206, 1)",
                pointBackgroundColor: "rgba(90, 179, 206, 1)",
                pointBorderColor: "#fff",
                pointHoverBackgroundColor: "#fff",
                pointHoverBorderColor: "rgba(90, 179, 206, 1)",
                data: queryVector
            }]
        };

        if (detailsRadarChart !== undefined)
            detailsRadarChart.destroy();

        detailsRadarChart = new Chart(attributeChart, {
            type: 'radar',
            data: data,
            draggable: true,
            options: {
                legend: {
                    position: 'bottom'
                },
                scale: {
                    ticks: {
                        display: false
                    }
                },
                tooltips: {
                    enabled: false
                }
            }
        });

        $(".details-overlay").animate({
            width: '400px'
        }, 300, function() {
            $(".details-content-wrapper").fadeIn(150);
            detailsExpanded = true;
        });
    };


    resultBox.click(function() {
        if (detailsExpanded) {
            var detailsBody = $(".details-body");
            detailsBody.fadeOut(200, function() {
                updateDetails();
                detailsBody.fadeIn(200);
            });
        } else
            updateDetails();
    });

    $(".tag").click(function() {
        var tag = $(this);
        var glyphicon = tag.children(".glyphicon");
        if (tag.hasClass("selected")) {
            tag.removeClass("selected");
            glyphicon.fadeOut(125, function() {
                glyphicon.removeClass("glyphicon-ok");
                glyphicon.addClass("glyphicon-remove");
                glyphicon.fadeIn(125);
            });

        } else {
            tag.addClass("selected");
            glyphicon.fadeOut(125, function() {
                glyphicon.addClass("glyphicon-ok");
                glyphicon.removeClass("glyphicon-remove");
                glyphicon.fadeIn(125);
            });
        }
    });

    $(".feature-btn").click(function() {
        var tagList = $(".tags .tag");
        var array = [];
        tagList.each(function() {
            var tag = $(this);
            if (!tag.hasClass("selected"))
                array.push($(this).text());
        });

        var app_id = "";
        if (currentAppID !== undefined)
            app_id = "app_id=" + currentAppID;

        var lib_vector = "";
        if (currentAppID == undefined)
            lib_vector = "only_library_vector=on";

        var user_vector = "";
        if ($('#user-vector-toggle').prop('checked'))
            user_vector = "&user_vector=on";

        var removed_features = "";
        if (array.length !== 0)
            removed_features = "&removed_features=" + btoa(array.join(","));

        window.location.replace("/?" + app_id + lib_vector + user_vector + removed_features);
    });

    $('.toggle-features-btn').click(function() {
        var btn = $(this);
        console.log(btn.text());
        if (btn.text() == "Show features to add/remove from suggestions")
            btn.text("Hide features to add/remove from suggestions");
        else
            btn.text("Show features to add/remove from suggestions");

        btn.blur();
    });
});
