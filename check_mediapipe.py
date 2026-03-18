import mediapipe as mp
print('module', mp)
print('attrs', [d for d in dir(mp) if not d.startswith('_')])
