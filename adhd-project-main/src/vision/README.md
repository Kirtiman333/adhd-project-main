Work flow eye_tracker:

INIT:
    1. Choose calibration: 5p / 9p / dense_grid / lissajous
       Choose filter agorithm: kalman / kalman_ema / kde / no smooth
    2. Create model has calibration config
        If has model then load_model
        Else then
            run calibration (update config)
            save_model in models folder
            load_model
    3. smoother = filter agorithm
    
LOOP:
    open_camera() (VideoCapture)
    for loop all frame
        feature = extract_feture(frame)
        check feature is not Blink (blink ~ no gaze)
            x,y = estimate()
            x_, y_ = smoother(x, y) #filter    
            draw(x_, y_)