import yuio.io

TEXT = """# Please edit lines below. Lines starting with '#' will be ignored.

Sing, O goddess, the anger of Achilles son of Peleus,
that brought countless ills upon the Achaeans.
Many a brave soul did it send hurrying down to Hades,
and many a hero did it yield a prey to dogs and vultures,
for so were the counsels of Jove fulfilled from the day on which the son of Atreus,
king of men, and great Achilles, first fell out with one another.
"""

if __name__ == '__main__':
    yuio.io.info('Yuio\'s interactive editing showcase.')
    yuio.io.info('')
    yuio.io.info('This functionality is similar to what GIT does when you commit something:')
    yuio.io.info('it opens your default editor and lets you edit a commit message.')
    yuio.io.info('')

    yuio.io.wait_for_user()

    result = yuio.io.edit(TEXT)

    yuio.io.info('<c:success>Editing successful!</c>')
    yuio.io.info('<c:green>So, this is what you\'ve done to Homer\'s Iliad:</c>')
    yuio.io.info('')
    yuio.io.info(result)
