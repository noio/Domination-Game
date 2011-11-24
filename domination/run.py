#!/usr/bin/env python
""" Domination game engine for Reinforcement Learning research.

Contains functions for running multiple games and tournaments.

"""
__author__ = "Thomas van den Berg and Tim Doolan"
__version__ = "1.0"

### IMPORTS ###
# Python
import datetime
import sys
import cPickle as pickle
import zipfile
from optparse import OptionParser

# Local
import core


### PROCEDURES ###

def games(red_brain='agent.py', 
              blue_brain='agent.py',
              red_brain_string=None,
              blue_brain_string=None,
              red_init={},
              blue_init={},
              settings=core.Settings(),
              field=None, 
              games=1, 
              record=None, 
              rendered=True,
              output=None,
              new_maps=True):
    """ Convenience function for running a number of games, storing
        the score as ( red_score / max_score ) for each game.
        Can also score replays as a zip file.
        
        :param field:    Contrary to Game(), the field argument here is an
                           ASCII representation of the desired field, as output
                           by field.to_file()
        :param record:   If set to true, records replay to a .pickle file.
                           For multiple games, a .zip file. 
        :param output:   Filename of file to APPEND scores to (or None).
        :param new_maps: Set to True to use a new map for each game.
        
    """
    scores  = []
    replays = []
    game    = None
    for i in xrange(games):
        if new_maps or game is None:
            game = core.Game(red_brain, blue_brain, red_brain_string, blue_brain_string,
                        red_init=red_init, blue_init=blue_init,
                        field=Field(from_string=open(field,'r').read()) if field is not None else None,
                        settings=settings,
                        record=record is not None,
                        rendered=rendered, verbose=False)
        game.run()
        print '[run_games]: Ran %d/%d games.'%(i+1,games)
        if game.interrupted:
            break
        scores.append(game.score_red/float(settings.max_score))
        replays.append(game.replay)
    # Store output if desired
    now = datetime.datetime.now()
    if output is not None:
        f = open(output,'a')
        t = now.strftime("%Y-%m-%d %H:%M:%S")
        f.write('# %dx %r (%s)\n'%(games,game,t))
        f.write(','.join('%.3f'%s for s in scores))
        f.write('\n')
    # Store replays if desired
    if record is not None:
        replays = [pickle.dumps(r) for r in replays]
        if record == 'AUTO':
            filename = 'replay_%s_%s_vs_%s'%(now.strftime("%Y%m%d_%H%M"),game.red_name,game.blue_name)
        else:
            filename = record
        if games == 1:
            f = open(filename+'.pickle','wb')
            f.write(replays[0])
            f.close()
        else:
            zf = zipfile.ZipFile(filename+'.zip','w')
            for i,r in enumerate(replays):
                zf.writestr('replay_%04d.pickle'%i,r)
            zf.close()
    return scores

### COMMAND LINE ###
if __name__ == '__main__':
    parser = OptionParser()
    default_settings = core.Settings()
    parser.add_option("-g", "--games", help="Number of games to play [default: %default]", default=1)
    parser.add_option("-r", "--red", help="Filename for the red agent [default: %default]", default="agent.py")
    parser.add_option("-b", "--blue", help="Filename for the blue agent [default: %default]", default="agent.py")
    parser.add_option("--red_init", help="Extra arguments that will be passed to the red agents' constructors, formatted as a python dict.", default='{}',metavar='"{key:val}"')
    parser.add_option("--blue_init", help="Extra arguments for blue agents.", default='{}',metavar='"{key:val}"')
    parser.add_option("-p", "--play", help="Filename of replay to play back.", default=None)
    parser.add_option("-o", "--output", help="Output file to which results will be appended.", default=None)
    parser.add_option("-i", "--invisible", help="Run the game without rendering.", action="store_false", dest='rendered', default=True)
    parser.add_option("-c", "--record", help="File to record replay(s) to (w/o extension). AUTO for automatic filename.", default=None)
    # Game Settings
    parser.add_option("-f", "--field", help="Filename of the field file to play on.", default=None)
    parser.add_option("--max_steps", help="Maximum game length. [default: %default]", default=default_settings.max_steps)
    parser.add_option("--max_see", help="Maximum observation range. [default: %default]", default=default_settings.max_see)
    parser.add_option("--field_width", help="Width of randomly generated field. [default: %default]", default=default_settings.field_width)
    parser.add_option("--field_height", help="Height of randomly generated field. [default: %default]", default=default_settings.field_height)
    parser.add_option("--num_agents", help="Number of agents per team. [default: %default]", default=default_settings.num_agents)
    (options, args) = parser.parse_args()
    if len(sys.argv) < 2:
        parser.print_help()
        print
        quit()
        
    if options.play is not None:
        pickle.load(open(options.play)).play()
    else:
        settings = core.Settings(max_steps=int(options.max_steps),
                            max_see=int(options.max_see),
                            field_width=int(options.field_width),
                            field_height=int(options.field_height),
                            num_agents=int(options.num_agents))
        run_games(red_brain=options.red, 
                  blue_brain=options.blue, 
                  red_init=eval(options.red_init),
                  blue_init=eval(options.blue_init),
                  settings=settings,
                  field=options.field,
                  games=int(options.games),
                  record=options.record, 
                  rendered=options.rendered,
                  output=options.output)
