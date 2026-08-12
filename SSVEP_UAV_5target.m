%% =========================================================
%  SSVEP 五目标刺激范式
%
%  文字位于刺激块上方
%  白色方块整体闪烁
%  红色文字标签
%
%  前进  6Hz
%  后退  7.5Hz
%  左移  8.57Hz
%  右移  10Hz
%  起飞  12Hz
%
%  ESC退出
%
%% =========================================================


sca;
clear;
clc;


%% ===============================
% Psychtoolbox初始化
% ===============================

PsychDefaultSetup(2);

Screen('Preference','SkipSyncTests',1);


screens=Screen('Screens');

screenNumber=max(screens);



%% ===============================
% 颜色
% ===============================

black=[0 0 0];

white=[255 255 255];




%% ===============================
% 打开窗口
% ===============================


[window,windowRect]=PsychImaging('OpenWindow',...
    screenNumber,...
    black);



[xCenter,yCenter]=RectCenter(windowRect);





%% ===============================
% 刷新率
% ===============================


ifi=Screen('GetFlipInterval',window);

fps=round(1/ifi);


fprintf("刷新率 %.2f Hz\n",1/ifi);






%% ===============================
% SSVEP参数
% ===============================


freq=[
    6
    7.5
    8.57
    10
    12
];



labels={
    '前进'
    '后退'
    '左移'
    '右移'
    '起飞'
};


N=length(freq);






%% ===============================
% 创建红色文字纹理
% ===============================


textTextures=zeros(1,N);



for i=1:N


    fig=figure(...
        'Visible','off',...
        'Color','black',...
        'Position',[100 100 260 100]);



    axis off;


    text(...
        0.5,...
        0.5,...
        labels{i},...
        'FontSize',50,...
        'FontName','Microsoft YaHei',...
        'Color',[1 1 1],...
        'HorizontalAlignment','center',...
        'VerticalAlignment','middle');


    axis([0 1 0 1]);



    frame=getframe(fig);


    close(fig);



    img=frame.cdata;



    textTextures(i)=Screen('MakeTexture',...
        window,...
        img);


end







%% ===============================
% 五个刺激位置
%
%
%              前进
%
%
% 左移                  右移
%
%
%              起飞
%
%
%              后退
%
%% ===============================



distance=600;



pos=[

    xCenter, yCenter-450;

    xCenter, yCenter+450;

    xCenter-600, yCenter;

    xCenter+600, yCenter;

    xCenter, yCenter

];








%% ===============================
% 刺激方框
% ===============================


boxSize=260;



rects=zeros(4,N);



for i=1:N

    rects(:,i)=CenterRectOnPoint(...
        [0 0 boxSize boxSize],...
        pos(i,1),...
        pos(i,2));

end







%% ===============================
% 键盘
% ===============================


KbName('UnifyKeyNames');


escKey=KbName('ESCAPE');






%% ===============================
% 开始
% ===============================


vbl=Screen('Flip',window);


frameCount=0;






%% ===============================
% 主循环
% ===============================


while true



    frameCount=frameCount+1;



    % ESC

    [keyDown,~,keyCode]=KbCheck;


    if keyDown
        
        if keyCode(escKey)
            break;
        end
        
    end






    for i=1:N



        %% ======================
        % 闪烁控制
        %% ======================


        period=fps/freq(i);


        phase=mod(frameCount,...
            round(period));



        if phase < period/2

            stimColor=white;

        else

            stimColor=black;

        end






        %% ======================
        % 绘制整体闪烁块
        %% ======================


        Screen('FillRect',...
            window,...
            stimColor,...
            rects(:,i));






        %% ======================
        % 绘制文字（刺激块上方）
        %% ======================


        textRect=CenterRectOnPoint(...
            [0 0 180 70],...
            pos(i,1),...
            pos(i,2)-boxSize/2-50);



        Screen('DrawTexture',...
            window,...
            textTextures(i),...
            [],...
            textRect);



    end







    %% ======================
    % 刷新
    %% ======================


    vbl=Screen('Flip',...
        window,...
        vbl+0.5*ifi);



end







%% ===============================
% 退出
% ===============================


sca;


disp("SSVEP刺激结束");