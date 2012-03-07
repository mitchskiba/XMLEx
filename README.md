

# WHY?!?

I'll start with the biggest WTF on this project. Why would I want to use somthing as verbose as XML to define somthing usually known to be sleek like regex?

## Maintainability.
If You were asked to figure out why the below regex didn't match something you expected it to, where would you start? How do you know what it even does?
`(SH|RE|MF)-((?:197[123456789]|19[89]\d|[23456789]\d{3})-(?:0[123456789]|1[012])-(?:0[123456789]|[12]\d|3[01]))-((?!0{5})\d{5})`

That is the example regex I built with this project. It is one of the three two digit codes, a dash, a YYYY-MM-DD date (after Jan 1, 1971) a dash, then a non 00000 5 digit number.

## Business Knowledge

I have heard some smart people say they shy away from using regex to enforce anything that could be considered business logic. In the dense form above, there isn't room to explain why anything is the way it is. Even an inline regex comment or two wouldn't save it.

This is a real shame given how useful regex can be for enforcing constraints.

# How

First, A disclaimer: Currently there is not a formal definition for the XML schema I use (and the code is quite hacked together and subject to change as I feel like revisiting this project). Ths whole thing is more or less a proof of concept anyway.

## XML Tags Used
__lit__ Short for literal. Contains text that will appear as represented in the XML document. That means you have to use XML entities for things like & (&amp;) and < (&gt;) etc.

__seq__ Short for sequence. Contains a list of sub-expressions to be matched in order

__or__ Contains a list of sub-expressions that may appear next

__mult__ Short for Multiplicity. Makes the single sub expression have a different multiplicity. Attributes *min* and *max* are used to control what kind of multiplicity it has.

__whitespace, not_whitespace, digit, not_digit, word_char, not_word_char, any, word_boundary, line_start, line_end, string_start, string_end__ These are all tags for the built in character classes and positions.

__class__ Defines a character class. The values attribute will be escaped, so place a list of literal characters in there. If you wish to use an exisiting character class as well, you can put it inside the body. Setting the *negative* attribute to true will make it a negated character class.

__macro__ Defines a named regular expression that can be inserted with the __use__ tag. The __macro__ tag expects a *name* attribute and a single child that will be put in pace of the use tag. The tag itself will not output anything. It is recommended that all macros go inside a sequence in a file included as a library. Also, don't put capture groups inside macros. Bad things may happen.

__use__ Substituted with the regular expression defined with __macro__ that shares the *name* attribute's value with this tag.

__set, clear__ Used to set/clear the imx flags of the single sub expression. Use the *flags* attribute to specify which flags should be changed.

__capture__ Used to define a capture group sorrounding the single sub expression. Optionally has a *name* attribute to make it a nammed capture group

__backref__ Used to make a backreference to a capture. Use either the *name* or *number* attribute. I recommend using *name* for both capture and backref. Even if your language does not support nammed backreferences, the compiler has the --force-numeric option that will do the position counting for you.

__group__ Makes a special grouping for the sorrounded subgroup. Valid types are "negative lookahead", "positive lookahead" and "nest"

## Compiler Options

 

	Usage: inputfile outputfile [Options]

	Options:
	  -h, --help            show this help message and exit
	  -l LIBRARY, --lib=LIBRARY
							library to consult for macros
	  --force-numeric       Force use of numeric capture groups only
	  -a LANGUAGE, --lang=LANGUAGE
							Language to target. Options are
							[ruby|python|.NET|pcre]
