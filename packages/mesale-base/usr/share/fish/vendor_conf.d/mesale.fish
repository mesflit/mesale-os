# Greet new fish shells with a system summary instead of fish's welcome text.
# Nothing is shown when fastfetch is not installed. A fish_greeting in the user's
# own config.fish is loaded later and replaces this one.
function fish_greeting
    if command -q fastfetch
        fastfetch
    end
end
