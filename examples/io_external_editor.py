import yuio.io

TEXT = """# Please edit the lines below. Lines starting with '#' will be ignored.

Sing, O goddess, the anger of Achilles son of Peleus,
that brought countless ills upon the Achaeans.
Many a brave soul did it send hurrying down to Hades,
and many a hero did it yield a prey to dogs and vultures,
for so were the counsels of Jove fulfilled from the day on which the son of Atreus,
king of men, and great Achilles, first fell out with one another.
"""

if __name__ == "__main__":
    yuio.io.heading("Yuio's interactive editing showcase")

    yuio.io.info(
        "This functionality is similar to what GIT does when you commit something: "
        "it opens your default editor and lets you edit a commit message."
    )

    yuio.io.br()

    yuio.io.wait_for_user()

    result = yuio.io.edit(TEXT, comment_marker="#")

    yuio.io.br()

    yuio.io.success("Editing successful!")
    yuio.io.success("So, this is what you've done to Homer's Iliad:")

    yuio.io.br()

    if result:
        yuio.io.info("%s", result)
    else:
        yuio.io.info("...\n\n... nothing! You've deleted it! How could you 〈◕﹏◕〉")
