# =============================================================================
# Toontown Beta Explorer
# Authors: Joey Ziolkowski, Ooowoo
# Date: 10/9/2020
#
# Purpose: Loads Bam and DNA files from Toontown Online Beta (v1.0.5) for
#          easy viewing. This tool must be ran with the same Python version
#          bundled with the Toontown Online Beta install. See README for
#          instructions.
#
# Usage: BETA_INSTALL_PATH/python.exe -O ToontownBetaExplorer.py "path/to/file.ext"
# =============================================================================

# If you moved the 1.0.5-install directory or downloaded it separately,
# update this variable with the correct location on your computer.
BETA_INSTALL_PATH = "../../Releases/ToontownBeta/1.0.5-install"

# Add paths to search for for beta files
import sys
sys.path.append(BETA_INSTALL_PATH + "/phase_2/lib/py")
sys.path.append(BETA_INSTALL_PATH + "/phase_3/lib/py")
import time

import Actor
import libtoontownModules
from libdirectGlobals import takeSnapshot
import ToontownGlobals
import DirectObject
import Vec4
from DepthTestProperty import *
from DepthTestTransition import *
from DepthWriteTransition import *
import ClockObject
from DirectNotifyGlobal import directNotify

globalClock = ClockObject.ClockObject.getGlobalClock()
notify = directNotify.newCategory('ToontownBetaExplorer')

# Store a dictionary of actor files and their file path. This is used for loading animation.
ACTOR_REFERENCE = {
    # Classic Characters
    # There are actually 2 'mickey-1200' models; however,
    # the one in phase_3 is the only one that needs to be
    # referenced in this dict
    # (see the Mickey special case below for more info
    # about the other 'mickey-1200')
    'mickey-1200': 'phase_3/models/char',
    'TT_MK-1500': 'phase_3/models/char',
    'minnie-1200': 'phase_4/models/char',
    'TT_D-1500': 'phase_6/models/char',
    'TT_G-1500': 'phase_6/models/char',
    'TT_MN-1500': 'phase_6/models/char',
    'donald-wheel-mod': 'phase_6/models/char',
    # Cogs
    'suitA-mod': 'phase_4/models/char',
    'suitB-mod': 'phase_4/models/char',
    'suitC-mod': 'phase_4/models/char',
    # Props
    'book-mod': 'phase_4/models/props',
    'portal-mod': 'phase_4/models/props',
    'stormcloud-mod': 'phase_4/models/props',
}

TOON_ACTOR_ELEMENTS = (
    ['dogSS_Shorts', 'dogMM_Shorts', 'dogLL_Shorts', 'dogSS_Skirt', 'dogMM_Skirt', 'dogLL_Skirt'],
    ['head', 'torso', 'legs'],
    ['1000']
)

NON_ACTOR_SUBSTRINGS = ('-1500', '-1000', '-1200', '-500', '-250', '-800', '-400', '-mod', '-heads')

PROP_ACTOR_ELEMENTS = (
    ['1dollar-bill', 'anvil', 'banana-peel', 'birthday-cake', 'calculator', 'clip-on-tie', 'feather', 'firehose',
     'cubes', 'flowerpot', 'glass', 'hypnotize', 'marbles', 'piano', 'propeller', 'rake', 'rake-step',
     'rubber-stamp-pad', 'safe', 'sandbag', 'sharpener', 'smile', 'splat', 'tnt', 'weight'],
    ['mod']
)


def product(*args, **kwds):
    """
    Reimplemented from itertools, which isn't supported in Python 2.0

    Example Usage:
        product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
        product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111

    Returns:
        list: Cartesian product of input.
    """
    pools = map(tuple, args) * kwds.get('repeat', 1)
    result = [[]]
    for pool in pools:
        result = [x+[y] for x in result for y in pool]
    return result


# Generate cartesian product of TOON_ACTOR_ELEMENTS and append to ACTOR_REFERENCE to store all Toon base models.
for element in product(*TOON_ACTOR_ELEMENTS):
    baseModel = '-'.join(element)  # Join all parts with '-'
    ACTOR_REFERENCE[baseModel] = 'phase_3/models/char'


# These are used for a special case to differentiate the 'book' toon animation from the book model
TOON_BOOK_ANIM_PATHS = []
TOON_BOOK_ANIMS = (
    ['dogSS_Shorts', 'dogMM_Shorts', 'dogLL_Shorts', 'dogSS_Skirt', 'dogMM_Skirt', 'dogLL_Skirt'],
    ['head', 'torso', 'legs'],
    ['book']
)
# Generate cartesian product of TOON_BOOK_ANIMS and append to TOON_BOOK_ANIM_PATHS.
for element in product(*TOON_BOOK_ANIMS):
    baseModel = '-'.join(element)  # Join all parts with '-'
    TOON_BOOK_ANIM_PATHS.append(baseModel)

# Generate cartesian product of PROP_ACTOR_ELEMENTS and append to ACTOR_REFERENCE to store all Battle Prop models.
for element in product(*PROP_ACTOR_ELEMENTS):
    baseModel = '-'.join(element)  # Join all parts with '-'
    ACTOR_REFERENCE[baseModel] = 'phase_5/models/props'


class ToontownBetaLoader(DirectObject.DirectObject):
    """
    Loader class for Toontown Beta files.
    """
    def __init__(self):
        # Use these to override the default paths because the default paths don't have
        # '../../Releases/ToontownBeta/1.0.5-install/'
        sndClick = base.loadSfx('../../Releases/ToontownBeta/1.0.5-install/phase_3/audio/sfx/GUI_create_toon_fwd.mp3')
        sndRollover = base.loadSfx('../../Releases/ToontownBeta/1.0.5-install/phase_3/audio/sfx/GUI_rollover.mp3')
        import GuiGlobals
        GuiGlobals.sndRollover = sndRollover
        GuiGlobals.sndClick = sndClick
        GuiGlobals.setDefaultFont(ToontownGlobals.getInterfaceFont())
        GuiGlobals.setDefaultPanel('phase_3/models/props/panel')
        import DirectGuiGlobals
        DirectGuiGlobals.sndRollover = sndRollover
        DirectGuiGlobals.sndClick = sndClick
        DirectGuiGlobals.setDefaultFont(ToontownGlobals.getInterfaceFont())
        import DialogBox
        self.popup = DialogBox.DialogBox(style=DialogBox.Acknowledge, doneEvent='popup-done')
        self.popup.hide()
        self.accept('popup-done', self.closePopUp)
        self.exitUponPopupClose = 0

        # Set the background color to the default in newer Panda versions
        # so we can actually see everything
        base.win.getGsg().setColorClearValue(Vec4.Vec4(0.5, 0.5, 0.5, 1))

        # Screenshot
        self.accept('f9', self.screenshot)

    def screenshot(self):
        """
        Takes a screenshot
        """
        # We're using this instead of ShowBase so we can create jpg files
        # The file extension can be changed in configrc
        date = time.ctime(time.time())
        frameCount = globalClock.getFrameCount()
        date = date.replace(' ', '-')
        date = date.replace(':', '-')
        imageName = 'tt-beta-explorer' + '-' + date + '-' + str(frameCount) + \
                    base.config.GetString('screenshot-file-extension', '.jpg')
        takeSnapshot(base.win, imageName)
        screenshotMsg = 'Screenshot taken. Check the ToontownBetaExplorer folder.'
        self.notifyPopUp(screenshotMsg, 0)
        notify.info(screenshotMsg)

    def notifyPopUp(self, text, exitUponClose=1):
        """
        Creates a little pop up box on the screen with text.

        Args:
            text (string): The message to display in the pop up box.
            exitUponClose (bool): Whether to terminate the program upon closing the pop up box or not.
        """
        self.popup.setMessage(text)
        self.popup.show()
        self.exitUponPopupClose = exitUponClose

    def closePopUp(self):
        """
        Closes the pop up box and terminates the program if exitUponPopupClose is true.
        """
        self.popup.hide()
        if self.exitUponPopupClose:
            sys.exit()
        else:
            self.exitUponPopupClose = 0

    def loadFile(self, filePath):
        """
        Parses Toontown Beta file path to determine how it should be loaded.

        Args:
            filePath (string): Path to the file to load.
        """
        if filePath[-3:] == 'bam':
            # Handle Bam files, used for models and animation
            self.loadBam(filePath)
        elif filePath[-3:] == 'dna':
            # Handle DNA files, used for levels
            self.loadDNA(filePath)
        else:
            badFileMsg = "Sorry, that file format isn't supported! Try dropping in a '.bam' or '.dna' file."
            self.notifyPopUp(badFileMsg)
            notify.warning(badFileMsg)

    def loadBam(self, filePath):
        """
        Loads a Toontown Beta Bam file.

        Args:
            filePath (string): Path to Bam file to load.
        """
        # 0 for model, 1 for anim
        typeFlag = 0

        # First, we need to check if this Bam file is an animation.
        geom = base.loader.loadModel(filePath)

        if not typeFlag:
            node = geom.find('**/+AnimBundleNode;+s')
            if not node.isEmpty():
                # It's an Anim
                geom.removeNode()
                typeFlag = 1

        if typeFlag:
            for actorBase, actorPhase in ACTOR_REFERENCE.items():
                actorBaseShortened = actorBase

                # This improves the accuracy of finding the model
                for substr in NON_ACTOR_SUBSTRINGS:
                    removingIdx = actorBase.find(substr)
                    if removingIdx > -1:
                        actorBaseShortened = actorBase[:removingIdx]

                if filePath.find(actorBaseShortened) > -1:
                    # Special case for the 'book' animation on toons so it doesn't load
                    # the book model
                    if actorBaseShortened == 'book':
                        for substr in TOON_BOOK_ANIM_PATHS:
                            if filePath.find(substr) > -1:
                                actorBase = substr[:-4] + '1000'
                                actorPhase = 'phase_3/models/char'

                    # Special case for Mickey's animations; both ToonTag Mickey
                    # and the early version of normal Mickey share the same animation
                    # filenames so we have to differentiate them based on the
                    # phase file they're in
                    elif actorBaseShortened == 'TT_MK':
                        if filePath.find('phase_4') > -1:
                            actorBase = 'mickey-1200'
                            actorPhase = 'phase_4/models/char'
                    geom = Actor.Actor(actorPhase + '/' + actorBase, {'anim': filePath})
                    geom.loop('anim')
                    break

        geom.reparentTo(render)

        self.notifyPopUp('Successfully loaded "%s"!' % filePath, 0)

        return geom

    def loadDNA(self, filePath, loadSky=1):
        """
        Loads a Toontown Beta DNA file.

        Args:
            filePath (string): Path to DNA file to load.
        """
        fileParts = filePath.split('/')
        if fileParts[-1].find('storage') > -1:
            storageMsg = "Storage files just contain model definitions for other DNA files, " \
                         "so there's nothing to display! Try a non-storage DNA file."
            self.notifyPopUp(storageMsg)
            notify.warning(storageMsg)
            return

        # Load global DNA storage files
        storage = libtoontownModules.DNAStorage()
        libtoontownModules.loadDNAFile(storage, 'phase_4/dna/storage.dna', 0, 0)
        libtoontownModules.loadDNAFile(storage, 'phase_5/dna/storage_town.dna', 0, 0)

        # Load phase-specific DNA storage files, and set sky based on area
        if filePath.find('phase_4') > -1 or filePath.find('phase_5') > -1:
            # Toontown Central
            skyFile = 'phase_4/models/props/TT_sky'
            libtoontownModules.loadDNAFile(storage, 'phase_4/dna/storage_TT.dna', 0, 0)
            libtoontownModules.loadDNAFile(storage, 'phase_4/dna/storage_TT_sz.dna', 0, 0)
            libtoontownModules.loadDNAFile(storage, 'phase_5/dna/storage_TT_town.dna', 0, 0)
        elif filePath.find('phase_6') > -1:
            if filePath.find('donalds') > -1:
                # Donald's Dock
                skyFile = 'phase_6/models/props/BR_sky'
                libtoontownModules.loadDNAFile(storage, 'phase_6/dna/storage_DD.dna', 0, 0)
                libtoontownModules.loadDNAFile(storage, 'phase_6/dna/storage_DD_sz.dna', 0, 0)
                libtoontownModules.loadDNAFile(storage, 'phase_6/dna/storage_DD_town.dna', 0, 0)
            elif filePath.find('minnies') > -1:
                # Minnie's Melodyland
                skyFile = 'phase_6/models/props/MM_sky'
                libtoontownModules.loadDNAFile(storage, 'phase_6/dna/storage_MM.dna', 0, 0)
                libtoontownModules.loadDNAFile(storage, 'phase_6/dna/storage_MM_sz.dna', 0, 0)
                libtoontownModules.loadDNAFile(storage, 'phase_6/dna/storage_MM_town.dna', 0, 0)
        elif filePath.find('phase_8') > -1:
            if filePath.find('burrrgh') > -1:
                # The Brrrgh
                skyFile = 'phase_6/models/props/BR_sky'
                libtoontownModules.loadDNAFile(storage, 'phase_8/dna/storage_BR.dna', 0, 0)
                libtoontownModules.loadDNAFile(storage, 'phase_8/dna/storage_BR_sz.dna', 0, 0)
                libtoontownModules.loadDNAFile(storage, 'phase_8/dna/storage_BR_town.dna', 0, 0)
            elif filePath.find('daisys') > -1:
                # Daisy Gardens
                skyFile = 'phase_4/models/props/TT_sky'
                libtoontownModules.loadDNAFile(storage, 'phase_8/dna/storage_DG.dna', 0, 0)
                libtoontownModules.loadDNAFile(storage, 'phase_8/dna/storage_DG_sz.dna', 0, 0)
                libtoontownModules.loadDNAFile(storage, 'phase_8/dna/storage_DG_town.dna', 0, 0)
            elif filePath.find('donalds') > -1:
                # Donald's Dreamland
                skyFile = 'phase_8/models/props/DL_sky'
                libtoontownModules.loadDNAFile(storage, 'phase_8/dna/storage_DL.dna', 0, 0)
                libtoontownModules.loadDNAFile(storage, 'phase_8/dna/storage_DL_sz.dna', 0, 0)
                libtoontownModules.loadDNAFile(storage, 'phase_8/dna/storage_DL_town.dna', 0, 0)

        # Load main DNA file
        geom = libtoontownModules.loadDNAFile(storage, filePath, 0, 0)
        render.attachNewNode(geom)

        # Load skybox if wanted
        if loadSky:
            sky = base.loader.loadModel(skyFile)

            # Normally we would use CompassEffect to unlock the sky from camera rotation, but that wasn't
            # available in Panda3D until 2002. Need to figure out what Disney's method was prior to that effect.
            sky.reparentTo(camera)
            sky.setZ(-30)

            # Disable depth on skybox (The fun 2001 way of doing it!) so that it doesn't render over the scene
            dw = DepthWriteTransition.off()
            dt = DepthTestTransition(DepthTestProperty.MNone)
            sky.arc().setTransition(dw, 1)
            sky.arc().setTransition(dt, 1)
            sky.setBin('background', -100)

        self.notifyPopUp('Successfully loaded "%s"!' % filePath, 0)

        return geom


# Get file path from command line argument
filePath = sys.argv[1]

# Start Beta loader, attempt to load file path
betaLoader = ToontownBetaLoader()
betaLoader.loadFile(filePath)

# Enable camera controls
base.useTrackball()

# Open main window
base.run()
